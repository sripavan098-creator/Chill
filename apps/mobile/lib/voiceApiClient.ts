/**
 * HTTPS client for the Chill voice backend (milestone 3).
 *
 * Only used when `EXPO_PUBLIC_CHILL_API_URL` is set. The client sends audio to
 * the server for embedding, but never receives audio or embeddings back: the
 * API returns scores and statuses only.
 */

import { API_BASE_URL, REQUEST_TIMEOUT_MS } from '@/lib/config';
import { clearDeviceSession, getAccessToken, saveDeviceSession } from '@/lib/deviceSession';
import { VerificationOutcome } from '@/types';

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

/**
 * Verifies a login sample against the stored owner embedding.
 *
 * `forcedOutcome` is a developer override: it is only honoured by the local
 * mock, never sent to the backend.
 */
export async function verifyRemoteVoice(
  audioBase64: string,
  durationMs: number,
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
    body: JSON.stringify({ duration_ms: durationMs, audio_base64: audioBase64 }),
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
