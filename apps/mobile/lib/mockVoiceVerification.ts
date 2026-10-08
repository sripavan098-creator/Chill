/**
 * Mock server-side processing.
 *
 * v0.2 records real audio but has no model to analyze it. These helpers stand
 * in for the backend so the UI can show realistic latency and outcomes.
 */

import { VerificationOutcome, VerificationResult } from '@/types';

export const MAX_VERIFICATION_ATTEMPTS = 3;

const PROCESSING_MS = 1000;
const VERIFICATION_MS = 1500;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Simulates analysing one enrollment sample. Resolves once the caller may
 * safely delete the temporary recording.
 */
export async function processEnrollmentSample(): Promise<void> {
  await delay(PROCESSING_MS);
}

/**
 * Simulates verifying a login sample.
 *
 * `forcedOutcome` comes from the developer toggle so both the success and the
 * fallback path stay reachable without a real model.
 */
export async function mockVerify(
  forcedOutcome: VerificationOutcome,
  attempt: number,
): Promise<VerificationResult> {
  await delay(VERIFICATION_MS);

  const similarity = 0.6 + Math.random() * 0.39;
  const outcome: VerificationOutcome =
    forcedOutcome ?? (similarity >= 0.75 ? 'success' : 'failure');

  return {
    outcome,
    confidence: Number(similarity.toFixed(2)),
    reason:
      outcome === 'success'
        ? 'Voice matched the enrolled owner profile.'
        : 'Voice did not match closely enough.',
    attemptsRemaining: Math.max(MAX_VERIFICATION_ATTEMPTS - attempt, 0),
  };
}

/**
 * Simulates the recording phase of a login attempt.
 */
export async function simulateListen(listenMs = 2000): Promise<void> {
  await delay(listenMs);
}

// Mirrors the server's `app.core.phrases` generator so local-only mode shows
// the same kind of phrase without a backend.
const CODE_WORDS = ['alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot', 'golf'];

function pickThree(): string[] {
  const pool = [...CODE_WORDS];
  const chosen: string[] = [];
  for (let i = 0; i < 3; i += 1) {
    const index = Math.floor(Math.random() * pool.length);
    chosen.push(pool.splice(index, 1)[0]);
  }
  return chosen;
}

/** Returns a spoken challenge phrase for the mock flow. */
export function mockChallengePhrase(): string {
  const [first, second, third] = pickThree();
  return `Hey Chill, your code is ${first} ${second} ${third}`;
}
