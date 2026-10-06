/**
 * Chill API facade.
 *
 * There is no backend in v0.2. These calls are local and persist only
 * non-biometric metadata. Milestone 3 replaces them with HTTPS calls to the
 * FastAPI service.
 */

import {
  buildEnrollmentMetadata,
  clearEnrollmentMetadata,
  getConsentRecord,
  getEnrollmentMetadata,
  saveConsentRecord,
  saveEnrollmentMetadata,
} from '@/features/voice-auth/enrollmentStore';
import { mockVerify } from '@/lib/mockVoiceVerification';
import { STORAGE_KEYS, readJson, storage, writeJson } from '@/lib/storage';
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
 */
export async function recordConsent(granted: boolean): Promise<ConsentRecord> {
  await delay(300);
  const record: ConsentRecord = {
    granted,
    grantedAt: granted ? new Date().toISOString() : null,
    policyVersion: CONSENT_POLICY_VERSION,
  };
  await saveConsentRecord(record);
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
 * The clips are used only to confirm that all five samples were captured. The
 * temporary recordings have already been deleted, and only enrollment
 * metadata is written to the device.
 */
export async function createVoiceProfile(
  displayName: string,
  clips: EnrollmentClip[],
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
 */
export async function deleteVoiceProfile(): Promise<void> {
  await delay(600);
  await clearEnrollmentMetadata();
  await storage.removeItem(STORAGE_KEYS.ownerName);
  await storage.removeItem(STORAGE_KEYS.onboardingComplete);
}

/**
 * Mock voice verification. Delegates to the mock model so the developer
 * toggle can force a pass or fail.
 */
export async function verifyVoice(
  forcedOutcome: VerificationOutcome,
  attempt = 1,
): Promise<VerificationResult> {
  const metadata = await getEnrollmentMetadata();
  if (!metadata?.voiceEnrolled) {
    throw new ApiError('No voice profile is enrolled.', 'NO_PROFILE');
  }
  return mockVerify(forcedOutcome, attempt);
}
