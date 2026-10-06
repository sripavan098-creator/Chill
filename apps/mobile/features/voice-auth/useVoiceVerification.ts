import { useCallback, useRef, useState } from 'react';

import { RecorderOutcome, useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { MAX_VERIFICATION_ATTEMPTS, verifyVoice } from '@/lib/api';
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
 * Records a real (temporary) login sample, then runs the mock verification
 * step. The recording is deleted before the result is reported. The developer
 * toggle in `settings.simulateOutcome` forces a pass or fail so both the
 * success and fallback paths stay testable without a real model.
 */
export function useVoiceVerification() {
  const { voiceProfile, settings, setSimulateOutcome } = useChill();
  const [phase, setPhase] = useState<VerificationPhase>('idle');
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const attemptRef = useRef(0);

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
        );
        attemptRef.current = nextAttempt;
        setAttempt(nextAttempt);
        setResult(verification);
        setError(null);
        setPhase('result');
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
    attemptLimitReached,
    simulateFailure: settings.simulateOutcome === 'failure',
    setSimulateFailure,
    verify,
  };
}
