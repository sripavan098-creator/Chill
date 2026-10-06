/**
 * Shared Chill domain types.
 *
 * v0.1 is mock-only: no embeddings, no raw audio, no backend payloads.
 */

export type OnboardingStep =
  | 'welcome'
  | 'permissions'
  | 'consent'
  | 'enroll'
  | 'complete';

export type ClipStatus = 'idle' | 'recording' | 'recorded' | 'error';

export interface EnrollmentPhrase {
  id: string;
  index: number;
  text: string;
}

export interface EnrollmentClip {
  phraseId: string;
  status: ClipStatus;
  /** Mock duration in milliseconds. Real audio is never persisted in v0.1. */
  durationMs: number | null;
  /** Mock signal quality between 0 and 1, reported after a capture. */
  quality?: number;
  error?: string;
}

export interface ConsentRecord {
  granted: boolean;
  grantedAt: string | null;
  policyVersion: string;
}

export interface VoiceProfile {
  id: string;
  displayName: string;
  createdAt: string;
  /** Mock embedding size. A real embedding is never exposed to the client. */
  embeddingDimensions: number;
  phraseCount: number;
}

export type VerificationOutcome = 'success' | 'failure';

export interface VerificationResult {
  outcome: VerificationOutcome;
  /** Mock confidence score between 0 and 1. */
  confidence: number;
  reason: string;
  attemptsRemaining: number;
}

export interface VerificationAttempt {
  id: string;
  outcome: VerificationOutcome;
  confidence: number;
  createdAt: string;
}

export interface ChillSettings {
  /** Developer-only toggle used to force a mock verification outcome. */
  simulateOutcome: VerificationOutcome;
}
