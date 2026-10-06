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

/**
 * Recording lifecycle for a single enrollment phrase.
 *
 * `preparing` covers opening the audio session, `processing` covers the mock
 * analysis that runs after the file is captured.
 */
export type RecordingState =
  | 'idle'
  | 'preparing'
  | 'recording'
  | 'processing'
  | 'success'
  | 'error';

export type ClipStatus = 'idle' | 'preparing' | 'recording' | 'processing' | 'recorded' | 'error';

export interface EnrollmentPhrase {
  id: string;
  index: number;
  text: string;
}

export interface EnrollmentClip {
  phraseId: string;
  status: ClipStatus;
  /** Duration of the captured sample in milliseconds. */
  durationMs: number | null;
  /** Signal quality between 0 and 1, reported after a capture. */
  quality?: number;
  error?: string;
}

/**
 * Enrollment metadata persisted on the device.
 *
 * Raw audio is deliberately absent: only enrollment status is stored.
 */
export interface EnrollmentMetadata {
  voiceEnrolled: boolean;
  consentGranted: boolean;
  enrollmentCompletedAt: string;
  enrollmentVersion: string;
}

export type MicrophonePermissionStatus = 'undetermined' | 'granted' | 'denied';

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
