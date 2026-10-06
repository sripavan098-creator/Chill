import { useCallback, useState } from 'react';

import { MAX_VERIFICATION_ATTEMPTS, verifyVoice } from '@/lib/api';
import { simulateListen } from '@/lib/mockVoiceRecorder';
import { useChill } from '@/state/ChillContext';
import { VerificationResult } from '@/types';

export type VerificationPhase = 'idle' | 'listening' | 'verifying' | 'result' | 'error';

const MOCK_LISTEN_MS = 2000;

/**
 * Mock voice verification flow.
 *
 * The developer toggle in `settings.simulateOutcome` forces a pass or fail so
 * both the success and fallback paths stay testable without a real model.
 */
export function useVoiceVerification() {
  const { voiceProfile, settings, setSimulateOutcome } = useChill();
  const [phase, setPhase] = useState<VerificationPhase>('idle');
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<VerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const busy = phase === 'listening' || phase === 'verifying';
  const attemptLimitReached =
    attempt >= MAX_VERIFICATION_ATTEMPTS && result?.outcome === 'failure';

  const verify = useCallback(async () => {
    if (busy) return null;
    setError(null);
    setResult(null);
    setPhase('listening');

    try {
      await simulateListen(MOCK_LISTEN_MS);
      setPhase('verifying');

      const nextAttempt = attempt + 1;
      const verification = await verifyVoice(settings.simulateOutcome, nextAttempt);

      setAttempt(nextAttempt);
      setResult(verification);
      setPhase('result');
      return verification;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Voice verification could not run. Try again.',
      );
      setPhase('error');
      return null;
    }
  }, [attempt, busy, settings.simulateOutcome]);

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
    attempt,
    result,
    error,
    attemptLimitReached,
    simulateFailure: settings.simulateOutcome === 'failure',
    setSimulateFailure,
    verify,
  };
}
