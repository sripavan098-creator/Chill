import { useCallback, useRef, useState } from 'react';

import { RecorderOutcome, useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { MAX_VERIFICATION_ATTEMPTS, requestChallenge, verifyVoice } from '@/lib/api';
import { useChill } from '@/state/ChillContext';
import { VerificationResult } from '@/types';

export type VerificationPhase =
  | 'idle'
  | 'listening'
  | 'verifying'
  | 'result'
  | 'error';

const LOGIN_MAX_RECORDING_MS = 3000;

/**
 * Voice verification flow.
 *
 * Each attempt is a spoken challenge: the app fetches a phrase first, shows it
 * for the speaker to read, then records. The recording is deleted before the
 * result is reported. The developer toggle in `settings.simulateOutcome`
 * forces a pass or fail so both the success and fallback paths stay testable
 * without a real model.
 */
export function useVoiceVerification() {
  const { voiceProfile, settings, setSimulateOutcome } = useChill();
  const [phase, setPhase] = useState<VerificationPhase>('idle');
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [phrase, setPhrase] = useState<string | null>(null);

  const attemptRef = useRef(0);
  const challengeRef = useRef<string | null>(null);

  const handleOutcome = useCallback(
    async (outcome: RecorderOutcome) => {
      if (outcome.status !== 'success') {
        setError(outcome.error ?? 'Could not record. Please try again.');
        setPhase('error');
        return;
      }

      setPhase('verifying');
      try {
        const nextAttempt = attemptRef.current + 1;
        const sample = outcome.captured.audioBase64
          ? {
              audioBase64: outcome.captured.audioBase64,
              durationMs: outcome.captured.durationMs,
            }
          : null;
        const verification = await verifyVoice(
          settings.simulateOutcome,
          nextAttempt,
          sample,
          challengeRef.current ?? undefined,
        );
        attemptRef.current = nextAttempt;
        setAttempt(nextAttempt);
        setResult(verification);
        setError(null);
        setPhase('result');
        // Each challenge is single-use; the next attempt asks for a new phrase.
        challengeRef.current = null;
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Voice verification could not run. Try again.',
        );
        setPhase('error');
      }
    },
    [settings.simulateOutcome],
  );

  const recorder = useVoiceRecorder({
    maxMs: LOGIN_MAX_RECORDING_MS,
    processSample: false,
    onOutcome: handleOutcome,
  });

  const busy = phase === 'listening' || phase === 'verifying';
  const attemptLimitReached =
    attempt >= MAX_VERIFICATION_ATTEMPTS && result?.outcome === 'failure';

  const verify = useCallback(async () => {
    if (busy) return;
    setError(null);
    setResult(null);
    try {
      const challenge = await requestChallenge();
      challengeRef.current = challenge.challengeId;
      setPhrase(challenge.phrase);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not prepare a verification challenge. Try again.',
      );
      setPhase('error');
      return;
    }
    setPhase('listening');
    await recorder.start();
    // The recorder flips to `error` internally on failure; mirror that here.
    if (recorder.state === 'error') {
      setPhase('error');
    }
  }, [busy, recorder]);

  const setSimulateFailure = useCallback(
    (next: boolean) => {
      void setSimulateOutcome(next ? 'failure' : 'success');
    },
    [setSimulateOutcome],
  );

  return {
    hasProfile: Boolean(voiceProfile),
    phase,
    busy,
    elapsedMs: recorder.elapsedMs,
    attempt,
    result,
    error: error ?? recorder.error,
    phrase,
    attemptLimitReached,
    simulateFailure: settings.simulateOutcome === 'failure',
    setSimulateFailure,
    verify,
  };
}
