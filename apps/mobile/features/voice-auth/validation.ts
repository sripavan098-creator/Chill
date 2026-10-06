/**
 * Enrollment recording rules.
 *
 * Kept free of React Native imports so the rules stay unit-testable.
 */

export const MIN_RECORDING_MS = 1500;
export const MAX_RECORDING_MS = 8000;

export const TOO_SHORT_MESSAGE = 'Please speak a little longer.';
export const TOO_LONG_MESSAGE = 'That sample was too long. Recording stopped automatically.';

export type DurationVerdict = 'ok' | 'too-short' | 'too-long';

export interface DurationValidation {
  verdict: DurationVerdict;
  /** User-facing message. `null` when the duration is acceptable. */
  message: string | null;
  /** Clamped duration in milliseconds. */
  durationMs: number;
}

export function validateDuration(durationMs: number): DurationValidation {
  if (durationMs < MIN_RECORDING_MS) {
    return { verdict: 'too-short', message: TOO_SHORT_MESSAGE, durationMs };
  }
  if (durationMs > MAX_RECORDING_MS) {
    return {
      verdict: 'too-long',
      message: TOO_LONG_MESSAGE,
      durationMs: MAX_RECORDING_MS,
    };
  }
  return { verdict: 'ok', message: null, durationMs };
}

export function isDurationAcceptable(durationMs: number): boolean {
  return validateDuration(durationMs).verdict === 'ok';
}
