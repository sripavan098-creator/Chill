import { useCallback, useEffect, useRef, useState } from 'react';

import { MAX_RECORDING_MS, validateDuration } from '@/features/voice-auth/validation';
import {
  CapturedRecording,
  RecordingHandle,
  discardRecording,
  startRecording,
} from '@/lib/audioRecorder';
import { processEnrollmentSample } from '@/lib/mockVoiceVerification';
import { RecordingState } from '@/types';

const TIMER_MS = 100;

export interface RecorderOutcome {
  status: 'success' | 'error';
  /** Duration and quality only. The temporary file is already deleted. */
  captured: CapturedRecording;
  error: string | null;
}

export interface UseVoiceRecorderOptions {
  /** Recording stops automatically once this many milliseconds elapse. */
  maxMs?: number;
  /** Run the mock enrollment analysis step after capture. */
  processSample?: boolean;
  /**
   * Called once per completed recording, including auto-stopped ones. Use this
   * instead of an effect so callers react in the same tick the sample resolves.
   */
  onOutcome?: (outcome: RecorderOutcome) => void;
}

export interface UseVoiceRecorderResult {
  state: RecordingState;
  elapsedMs: number;
  error: string | null;
  /** Duration and quality of the last capture. The temp file is already gone. */
  captured: CapturedRecording | null;
  isActive: boolean;
  start: () => Promise<void>;
  stop: () => Promise<RecorderOutcome | null>;
  cancel: () => Promise<void>;
  reset: () => void;
}

/**
 * Single-session voice recorder.
 *
 * Owns the recording lifecycle, the visible timer, the mock processing step
 * and temporary-file cleanup. The temporary recording is deleted before the
 * hook reports an outcome, so no raw audio outlives the session.
 */
export function useVoiceRecorder(
  options: UseVoiceRecorderOptions = {},
): UseVoiceRecorderResult {
  const { maxMs = MAX_RECORDING_MS, processSample = true, onOutcome } = options;

  const [state, setState] = useState<RecordingState>('idle');
  const [elapsedMs, setElapsedMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [captured, setCaptured] = useState<CapturedRecording | null>(null);

  const handleRef = useRef<RecordingHandle | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stoppingRef = useRef(false);
  const stopRef = useRef<() => Promise<RecorderOutcome | null>>(async () => null);
  const onOutcomeRef = useRef(onOutcome);

  useEffect(() => {
    onOutcomeRef.current = onOutcome;
  }, [onOutcome]);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const stop = useCallback(async (): Promise<RecorderOutcome | null> => {
    if (stoppingRef.current) return null;
    const handle = handleRef.current;
    if (!handle) return null;

    stoppingRef.current = true;
    clearTimer();
    if (processSample) {
      setState('processing');
    }

    try {
      const result = await handle.stop();
      handleRef.current = null;

      if (processSample) {
        await processEnrollmentSample();
      }

      // Privacy: the temporary recording never outlives the processing step.
      await discardRecording(result.uri);

      const validation = validateDuration(result.durationMs);
      const sanitized: CapturedRecording = { ...result, uri: null };
      const outcome: RecorderOutcome =
        validation.verdict === 'ok'
          ? { status: 'success', captured: sanitized, error: null }
          : { status: 'error', captured: sanitized, error: validation.message };

      setCaptured(sanitized);
      setElapsedMs(validation.durationMs);
      setError(outcome.error);
      setState(outcome.status);
      onOutcomeRef.current?.(outcome);
      return outcome;
    } catch {
      const outcome: RecorderOutcome = {
        status: 'error',
        captured: { uri: null, durationMs: 0, quality: 0 },
        error: 'Could not record. Please try again.',
      };
      setCaptured(outcome.captured);
      setError(outcome.error);
      setState('error');
      onOutcomeRef.current?.(outcome);
      return outcome;
    } finally {
      stoppingRef.current = false;
    }
  }, [clearTimer, processSample]);

  // Refs are only written in effects so render stays free of side effects.
  useEffect(() => {
    stopRef.current = stop;
  }, [stop]);

  useEffect(() => {
    return () => {
      clearTimer();
      void handleRef.current?.cancel();
      handleRef.current = null;
    };
  }, [clearTimer]);

  const start = useCallback(async () => {
    if (handleRef.current) return;

    setError(null);
    setCaptured(null);
    setElapsedMs(0);
    setState('preparing');

    try {
      const handle = await startRecording();
      handleRef.current = handle;
      setState('recording');

      const startedAt = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = Date.now() - startedAt;
        setElapsedMs(Math.min(elapsed, maxMs));
        if (elapsed >= maxMs) {
          void stopRef.current();
        }
      }, TIMER_MS);
    } catch {
      handleRef.current = null;
      const outcome: RecorderOutcome = {
        status: 'error',
        captured: { uri: null, durationMs: 0, quality: 0 },
        error: 'Could not start recording. Check microphone access and try again.',
      };
      setError(outcome.error);
      setState('error');
      onOutcomeRef.current?.(outcome);
    }
  }, [maxMs]);

  const cancel = useCallback(async () => {
    clearTimer();
    stoppingRef.current = false;
    const handle = handleRef.current;
    handleRef.current = null;
    if (handle) {
      await handle.cancel();
    }
    setState('idle');
    setElapsedMs(0);
    setError(null);
    setCaptured(null);
  }, [clearTimer]);

  const reset = useCallback(() => {
    clearTimer();
    handleRef.current = null;
    stoppingRef.current = false;
    setState('idle');
    setElapsedMs(0);
    setError(null);
    setCaptured(null);
  }, [clearTimer]);

  return {
    state,
    elapsedMs,
    error,
    captured,
    isActive: state === 'preparing' || state === 'recording' || state === 'processing',
    start,
    stop,
    cancel,
    reset,
  };
}
