/**
 * Local persistence for voice enrollment.
 *
 * Only enrollment metadata is written. Raw audio and embeddings are never
 * stored here; v0.2 keeps the device free of biometric recordings.
 */

import { STORAGE_KEYS, readJson, storage, writeJson } from '@/lib/storage';
import { ConsentRecord, EnrollmentMetadata } from '@/types';

export const ENROLLMENT_VERSION = '0.2.0';

export async function saveEnrollmentMetadata(
  metadata: EnrollmentMetadata,
): Promise<void> {
  await writeJson(STORAGE_KEYS.enrollment, metadata);
}

export async function getEnrollmentMetadata(): Promise<EnrollmentMetadata | null> {
  return readJson<EnrollmentMetadata>(STORAGE_KEYS.enrollment);
}

export async function clearEnrollmentMetadata(): Promise<void> {
  await storage.removeItem(STORAGE_KEYS.enrollment);
}

export function buildEnrollmentMetadata(
  consentGranted: boolean,
  completedAt = new Date().toISOString(),
): EnrollmentMetadata {
  return {
    voiceEnrolled: true,
    consentGranted,
    enrollmentCompletedAt: completedAt,
    enrollmentVersion: ENROLLMENT_VERSION,
  };
}

export function isEnrollmentValid(
  metadata: EnrollmentMetadata | null,
): boolean {
  return Boolean(metadata?.voiceEnrolled);
}

export async function saveConsentRecord(record: ConsentRecord): Promise<void> {
  await writeJson(STORAGE_KEYS.consent, record);
}

export async function getConsentRecord(): Promise<ConsentRecord | null> {
  return readJson<ConsentRecord>(STORAGE_KEYS.consent);
}
