/**
 * HTTPS client for the Chill voice backend (milestone 3).
 *
 * Only used when `EXPO_PUBLIC_CHILL_API_URL` is set. The client sends audio to
 * the server for embedding, but never receives audio or embeddings back: the
 * API returns scores and statuses only.
 */

import { API_BASE_URL, REQUEST_TIMEOUT_MS } from '@/lib/config';
import { clearDeviceSession, getAccessToken, saveDeviceSession } from '@/lib/deviceSession';
import { BackendVersionPolicy, VerificationOutcome } from '@/types';

export class BackendError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'BackendError';
  }
}

interface ApiErrorBody {
  error?: { code?: string; message?: string };
}

async function parseError(response: Response): Promise<BackendError> {
  let code = 'REQUEST_FAILED';
  let message = 'The voice service could not complete the request.';
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body.error?.code) code = body.error.code;
    if (body.error?.message) message = body.error.message;
  } catch {
    // Non-JSON error body; keep the defaults.
  }
  return new BackendError(message, code, response.status);
}

async function request<T>(
  path: string,
  init: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const { token, headers, ...rest } = init;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...rest,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
    });

    if (!response.ok) {
      throw await parseError(response);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  } catch (error) {
    // Normalise network failures and timeouts into one retryable shape so
    // callers do not have to special-case the platform's fetch errors.
    if (error instanceof BackendError) throw error;
    if ((error as { name?: string })?.name === 'AbortError') {
      throw new BackendError(
        'The voice service took too long to respond. Please try again.',
        'NETWORK_ERROR',
        0,
      );
    }
    throw new BackendError(
      'Chill could not reach the voice service. Check your connection and try again.',
      'NETWORK_ERROR',
      0,
    );
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Registers this device once and stores the returned token securely.
 */
export async function ensureDeviceSession(platform: string): Promise<string> {
  const existing = await getAccessToken();
  if (existing) return existing;

  const session = await request<{
    owner_id: string;
    device_id: string;
    access_token: string;
  }>('/v1/devices', {
    method: 'POST',
    body: JSON.stringify({ platform, label: 'Chill mobile' }),
  });

  await saveDeviceSession({
    accessToken: session.access_token,
    ownerId: session.owner_id,
    deviceId: session.device_id,
  });
  return session.access_token;
}

export interface RemoteEnrollmentSample {
  phraseId: string;
  durationMs: number;
  quality: number;
  audioBase64: string;
}

/**
 * Uploads the enrollment samples for embedding. The server discards the raw
 * audio after computing the embedding; the app has already deleted its own
 * temporary copy by this point.
 */
export async function createRemoteEnrollment(
  samples: RemoteEnrollmentSample[],
  displayName: string,
): Promise<void> {
  const token = await ensureDeviceSession('mobile');
  await request('/v1/enrollment', {
    method: 'POST',
    token,
    body: JSON.stringify({
      display_name: displayName,
      samples: samples.map((sample) => ({
        phrase_id: sample.phraseId,
        duration_ms: sample.durationMs,
        quality: sample.quality,
        audio_base64: sample.audioBase64,
      })),
    }),
  });
}

export async function setRemoteConsent(granted: boolean): Promise<void> {
  const token = await ensureDeviceSession('mobile');
  await request('/v1/consent', {
    method: 'PUT',
    token,
    body: JSON.stringify({ granted }),
  });
}

export interface VoiceChallenge {
  challengeId: string;
  /** Phrase the server asks the speaker to say. Null when disabled. */
  phrase: string | null;
}

/**
 * Requests a single-use verification challenge.
 *
 * The caller shows `phrase` to the speaker before recording, then passes
 * `challengeId` to `verifyRemoteVoice`. Fetching the phrase first is what makes
 * the spoken check meaningful: the words were not known when any earlier
 * recording was made.
 */
export async function requestVoiceChallenge(): Promise<VoiceChallenge> {
  const token = await ensureDeviceSession('mobile');
  const challenge = await request<{ challenge_id: string; phrase: string | null }>(
    '/v1/verification/challenge',
    { method: 'POST', token },
  );
  return {
    challengeId: challenge.challenge_id,
    phrase: challenge.phrase ?? null,
  };
}

/**
 * Verifies a login sample against the stored owner embedding.
 *
 * `forcedOutcome` is a developer override: it is only honoured by the local
 * mock, never sent to the backend.
 */
export async function verifyRemoteVoice(
  audioBase64: string,
  durationMs: number,
  challengeId: string,
): Promise<{ outcome: VerificationOutcome; reason: string; attemptsRemaining: number }> {
  const token = await ensureDeviceSession('mobile');

  const result = await request<{
    outcome: string;
    reason: string;
    attempts_remaining: number;
    locked_out: boolean;
  }>('/v1/verification', {
    method: 'POST',
    token,
    body: JSON.stringify({
      duration_ms: durationMs,
      audio_base64: audioBase64,
      challenge_id: challengeId,
    }),
  });

  return {
    outcome: result.outcome === 'success' ? 'success' : 'failure',
    reason: result.locked_out
      ? 'Too many failed attempts. Use the PIN fallback.'
      : result.reason,
    attemptsRemaining: result.attempts_remaining,
  };
}

export async function deleteRemoteProfile(): Promise<void> {
  const token = await getAccessToken();
  if (!token) return;
  await request('/v1/profile', {
    method: 'DELETE',
    token,
    body: JSON.stringify({ confirm: 'DELETE' }),
  });
}

export async function deleteRemoteAccount(): Promise<void> {
  const token = await getAccessToken();
  if (token) {
    await request('/v1/account', {
      method: 'DELETE',
      token,
      body: JSON.stringify({ confirm: 'DELETE' }),
    });
  }
  await clearDeviceSession();
}

/** Fetches the backend client version policy. Public, so no device session. */
export async function fetchVersionPolicy(): Promise<BackendVersionPolicy> {
  const body = await request<{
    api_version: string;
    minimum_supported: string;
    latest: string;
    update_url: string;
  }>('/v1/version');

  return {
    apiVersion: body.api_version,
    minimumSupported: body.minimum_supported,
    latest: body.latest,
    updateUrl: body.update_url,
  };
}

/**
 * Files a feedback report. Deliberately carries no audio or embeddings: only
 * the message plus coarse device context.
 */
export async function sendRemoteFeedback(report: {
  kind: string;
  message: string;
  appVersion: string;
  platform: string;
}): Promise<{ id: string; kind: string }> {
  const token = await ensureDeviceSession('mobile');
  const result = await request<{ id: string; kind: string }>('/v1/feedback', {
    method: 'POST',
    token,
    body: JSON.stringify({
      kind: report.kind,
      message: report.message,
      app_version: report.appVersion,
      platform: report.platform,
    }),
  });
  return result;
}
