/**
 * The five enrollment phrases. Source of truth: docs/PRD.md
 */
import { EnrollmentClip, EnrollmentPhrase } from '@/types';

export const ENROLLMENT_PHRASES: EnrollmentPhrase[] = [
  { id: 'phrase-1', index: 0, text: 'Hey Chill, this is my voice.' },
  { id: 'phrase-2', index: 1, text: 'Hey Chill, unlock my assistant.' },
  { id: 'phrase-3', index: 2, text: 'Hey Chill, remember me.' },
  { id: 'phrase-4', index: 3, text: 'Hey Chill, keep my data private.' },
  { id: 'phrase-5', index: 4, text: 'Hey Chill, start listening.' },
];

export const REQUIRED_PHRASE_COUNT = ENROLLMENT_PHRASES.length;

export function createInitialClips(): EnrollmentClip[] {
  return ENROLLMENT_PHRASES.map((phrase) => ({
    phraseId: phrase.id,
    status: 'idle' as const,
    durationMs: null,
  }));
}
