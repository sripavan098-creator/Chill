/**
 * Chill API facade.
 *
 * Two modes:
 * - Local (default): calls are local and persist only non-biometric metadata.
 * - Backend: when `EXPO_PUBLIC_CHILL_API_URL` is set, voice enrollment,
 *   consent and verification go to the FastAPI service (milestone 3). The
 *   local enrollment metadata is still written so the UI works offline.
 */

import {
  buildEnrollmentMetadata,
  clearEnrollmentMetadata,
  getConsentRecord,
  getEnrollmentMetadata,
  saveConsentRecord,
  saveEnrollmentMetadata,
} from '@/features/voice-auth/enrollmentStore';
import { USE_REMOTE_API } from '@/lib/config';
import { mockVerify, mockChallengePhrase } from '@/lib/mockVoiceVerification';
import { STORAGE_KEYS, readJson, storage, writeJson } from '@/lib/storage';
import {
  createRemoteEnrollment,
  deleteRemoteProfile,
  requestVoiceChallenge,
  setRemoteConsent,
  verifyRemoteVoice,
} from '@/lib/voiceApiClient';
import type { RemoteEnrollmentSample, VoiceChallenge } from '@/lib/voiceApiClient';
import {
  ConsentRecord,
  EnrollmentClip,
  VerificationOutcome,
  VerificationResult,
  VoiceProfile,
} from '@/types';

export const CONSENT_POLICY_VERSION = '2026-10-01';
export const MAX_VERIFICATION_ATTEMPTS = 3;
const MOCK_EMBEDDING_DIMENSIONS = 192;

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * Records voice biometric consent. Consent must exist before enrollment.
 *
 * With a backend configured, consent is also registered server-side so the API
 * can gate enrollment. A backend failure does not lose the local record.
 */
export async function recordConsent(granted: boolean): Promise<ConsentRecord> {
  await delay(300);
  const record: ConsentRecord = {
    granted,
    grantedAt: granted ? new Date().toISOString() : null,
    policyVersion: CONSENT_POLICY_VERSION,
  };
  await saveConsentRecord(record);

  if (USE_REMOTE_API) {
    await setRemoteConsent(granted);
  }
  return record;
}

export async function getConsent(): Promise<ConsentRecord | null> {
  return getConsentRecord();
}

export async function withdrawConsent(): Promise<void> {
  await recordConsent(false);
}

/**
 * Finalises enrollment.
 *
 * The clips confirm that all five samples were captured. When a backend is
 * configured the in-memory samples are uploaded for embedding; the raw audio
 * is discarded by both the app and the server afterwards. Only enrollment
 * metadata is written to the device.
 */
export async function createVoiceProfile(
  displayName: string,
  clips: EnrollmentClip[],
  samples: RemoteEnrollmentSample[] = [],
): Promise<VoiceProfile> {
  await delay(900);

  const consent = await getConsent();
  if (!consent?.granted) {
    throw new ApiError('Voice consent is required before enrollment.', 'CONSENT_REQUIRED');
  }

  const usable = clips.filter((clip) => clip.status === 'recorded');
  if (usable.length < 5) {
    throw new ApiError('Five voice samples are required.', 'INCOMPLETE_ENROLLMENT');
  }

  const trimmedName = displayName.trim() || 'Chill owner';

  if (USE_REMOTE_API) {
    await createRemoteEnrollment(samples, trimmedName);
  }

  const metadata = buildEnrollmentMetadata(true);
  await saveEnrollmentMetadata(metadata);
  await writeJson(STORAGE_KEYS.ownerName, trimmedName);
  await writeJson(STORAGE_KEYS.onboardingComplete, true);

  return {
    id: createId('vp'),
    displayName: trimmedName,
    createdAt: metadata.enrollmentCompletedAt,
    embeddingDimensions: MOCK_EMBEDDING_DIMENSIONS,
    phraseCount: usable.length,
  };
}

/**
 * Rebuilds the display profile from persisted enrollment metadata.
 */
export async function getVoiceProfile(): Promise<VoiceProfile | null> {
  const metadata = await getEnrollmentMetadata();
  if (!metadata?.voiceEnrolled) return null;

  const displayName =
    (await readJson<string>(STORAGE_KEYS.ownerName)) ?? 'Chill owner';

  return {
    id: 'vp_local',
    displayName,
    createdAt: metadata.enrollmentCompletedAt,
    embeddingDimensions: MOCK_EMBEDDING_DIMENSIONS,
    phraseCount: 5,
  };
}

/**
 * Deletes the voice profile and its local enrollment metadata.
 *
 * With a backend configured the server-side embedding is deleted first; if
 * that fails the local metadata is kept so the user can retry rather than
 * leaving an orphaned server profile.
 */
export async function deleteVoiceProfile(): Promise<void> {
  await delay(600);
  if (USE_REMOTE_API) {
    await deleteRemoteProfile();
  }
  await clearEnrollmentMetadata();
  await storage.removeItem(STORAGE_KEYS.ownerName);
  await storage.removeItem(STORAGE_KEYS.onboardingComplete);
}

/**
 * Requests a spoken challenge for the next verification attempt.
 *
 * Remote mode returns the server's phrase, which the speaker must say. Local
 * mode returns a mock phrase so the UI flow is identical without a backend.
 */
export async function requestChallenge(): Promise<VoiceChallenge> {
  if (USE_REMOTE_API) {
    return requestVoiceChallenge();
  }
  return {
    challengeId: createId('ch'),
    phrase: mockChallengePhrase(),
  };
}

/**
 * Voice verification.
 *
 * With a backend configured the recorded sample is verified against the stored
 * embedding and the spoken challenge. Otherwise the mock model runs, so the
 * developer toggle can force a pass or fail.
 */
export async function verifyVoice(
  forcedOutcome: VerificationOutcome,
  attempt = 1,
  sample?: { audioBase64: string; durationMs: number } | null,
  challengeId?: string,
): Promise<VerificationResult> {
  const metadata = await getEnrollmentMetadata();
  if (!metadata?.voiceEnrolled) {
    throw new ApiError('No voice profile is enrolled.', 'NO_PROFILE');
  }

  if (USE_REMOTE_API && sample) {
    if (!challengeId) {
      throw new ApiError(
        'A verification challenge is required.',
        'CHALLENGE_REQUIRED',
      );
    }
    const remote = await verifyRemoteVoice(
      sample.audioBase64,
      sample.durationMs,
      challengeId,
    );
    return {
      outcome: remote.outcome,
      confidence: 0,
      reason: remote.reason,
      attemptsRemaining: remote.attemptsRemaining,
    };
  }

  return mockVerify(forcedOutcome, attempt);
}
