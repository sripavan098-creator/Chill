/**
 * Mock Chill API client.
 *
 * There is no backend in v0.1. Every call here is local and in-memory.
 * Milestone 3 replaces these functions with HTTPS calls to the FastAPI service.
 */

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
  constructor(message: string, readonly code: string) {
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
  await writeJson(STORAGE_KEYS.consent, record);
  return record;
}

export async function getConsent(): Promise<ConsentRecord | null> {
  return readJson<ConsentRecord>(STORAGE_KEYS.consent);
}

export async function withdrawConsent(): Promise<void> {
  await recordConsent(false);
}

/**
 * Creates a mock owner voice profile from completed enrollment clips.
 *
 * The clips are used only to count valid samples. No audio leaves the device
 * and no raw recording is stored.
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

  const profile: VoiceProfile = {
    id: createId('vp'),
    displayName: displayName.trim() || 'Chill owner',
    createdAt: new Date().toISOString(),
    embeddingDimensions: MOCK_EMBEDDING_DIMENSIONS,
    phraseCount: usable.length,
  };

  await writeJson(STORAGE_KEYS.voiceProfile, profile);
  return profile;
}

export async function getVoiceProfile(): Promise<VoiceProfile | null> {
  return readJson<VoiceProfile>(STORAGE_KEYS.voiceProfile);
}

export async function deleteVoiceProfile(): Promise<void> {
  await delay(600);
  await storage.removeItem(STORAGE_KEYS.voiceProfile);
}

/**
 * Mock voice verification.
 *
 * `forcedOutcome` lets the developer toggle in the login screen drive the
 * result. Without it the mock compares a random similarity against a threshold.
 */
export async function verifyVoice(
  forcedOutcome: VerificationOutcome | null = null,
  attempt = 1,
): Promise<VerificationResult> {
  await delay(400);

  const profile = await getVoiceProfile();
  if (!profile) {
    throw new ApiError('No voice profile is enrolled.', 'NO_PROFILE');
  }

  const similarity = 0.6 + Math.random() * 0.39;
  const outcome: VerificationOutcome =
    forcedOutcome ?? (similarity >= 0.75 ? 'success' : 'failure');

  const attemptsRemaining = Math.max(MAX_VERIFICATION_ATTEMPTS - attempt, 0);

  return {
    outcome,
    confidence: Number(similarity.toFixed(2)),
    reason:
      outcome === 'success'
        ? 'Voice matched the enrolled owner profile.'
        : 'Voice did not match closely enough.',
    attemptsRemaining,
  };
}
