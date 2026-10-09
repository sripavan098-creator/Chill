/**
 * Recording calibration.
 *
 * A shared target for the levels a phrase should hit: the enrollment phrases
 * and the login challenge both want a similar amount of speech. These are
 * heuristic bands derived from duration and quality; they are guidance, not a
 * security control, and a real model replaces them in a later milestone.
 */

/** Comfortable spoken duration for a single phrase, in milliseconds. */
export const CALIBRATION = {
  minDurationMs: 1500,
  /** Best-practice target shown to the speaker. */
  idealDurationMs: 2500,
  maxDurationMs: 8000,
  /** Quality (0–1) at or above which a sample is considered strong. */
  strongQuality: 0.75,
  /** Quality below which a re-record is recommended. */
  weakQuality: 0.45,
} as const;

export type CalibrationBand = 'weak' | 'good' | 'strong';

export interface CalibrationResult {
  band: CalibrationBand;
  /** Short, non-technical hint for the speaker. */
  hint: string;
  /** True when the sample should be recorded again. */
  shouldRetry: boolean;
}

/**
 * Grades a sample. Duration is treated first: a clip that is too short cannot
 * be strong no matter how clean it is.
 */
export function gradeSample(
  durationMs: number,
  quality: number,
): CalibrationResult {
  if (durationMs < CALIBRATION.minDurationMs) {
    return {
      band: 'weak',
      hint: 'That was a little short. Try a full sentence.',
      shouldRetry: true,
    };
  }
  if (quality < CALIBRATION.weakQuality) {
    return {
      band: 'weak',
      hint: 'It was hard to hear that. Move somewhere quieter and try again.',
      shouldRetry: true,
    };
  }
  if (
    durationMs >= CALIBRATION.idealDurationMs &&
    quality >= CALIBRATION.strongQuality
  ) {
    return { band: 'strong', hint: 'Clear sample — thanks.', shouldRetry: false };
  }
  return { band: 'good', hint: 'Good sample.', shouldRetry: false };
}