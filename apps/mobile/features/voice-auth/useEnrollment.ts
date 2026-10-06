import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { MAX_MOCK_DURATION_MS, createMockRecorder, isUsableClip } from '@/lib/mockVoiceRecorder';
import { ENROLLMENT_PHRASES, createInitialClips } from '@/lib/phrases';
import { useChill } from '@/state/ChillContext';
import { EnrollmentClip } from '@/types';

const TICK_MS = 250;

/**
 * Drives the mock enrollment recording flow: start, tick, stop, retry and
 * final profile creation. All recording state lives here so the screen stays
 * presentational.
 */
export function useEnrollment() {
  const { completeEnrollment } = useChill();
  const [clips, setClips] = useState<EnrollmentClip[]>(() => createInitialClips());
  const [activePhraseId, setActivePhraseId] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);

  const recorderRef = useRef<ReturnType<typeof createMockRecorder> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      stopTimer();
      recorderRef.current?.cancel();
    };
  }, [stopTimer]);

  const setClip = useCallback((phraseId: string, patch: Partial<EnrollmentClip>) => {
    setClips((prev) =>
      prev.map((clip) => (clip.phraseId === phraseId ? { ...clip, ...patch } : clip)),
    );
  }, []);

  const finishRecording = useCallback(
    async (phraseId: string, recorder: ReturnType<typeof createMockRecorder>) => {
      stopTimer();
      const session = await recorder.stop();
      recorderRef.current = null;
      setActivePhraseId(null);

      if (isUsableClip(session)) {
        setClip(phraseId, {
          status: 'recorded',
          durationMs: session.durationMs,
          quality: session.quality,
          error: undefined,
        });
      } else {
        setClip(phraseId, {
          status: 'error',
          durationMs: null,
          quality: 0,
          error: 'That sample was too short. Please hold the recording a little longer.',
        });
      }
    },
    [setClip, stopTimer],
  );

  const start = useCallback(
    (phraseId: string) => {
      const recorder = createMockRecorder();
      recorderRef.current = recorder;
      setActivePhraseId(phraseId);
      setClip(phraseId, {
        status: 'recording',
        durationMs: 0,
        quality: undefined,
        error: undefined,
      });

      timerRef.current = setInterval(() => {
        const session = recorder.tick((recorder.session.durationMs ?? 0) + TICK_MS);
        setClip(phraseId, { durationMs: session.durationMs });
        if (session.durationMs >= MAX_MOCK_DURATION_MS) {
          void finishRecording(phraseId, recorder);
        }
      }, TICK_MS);
    },
    [finishRecording, setClip],
  );

  const stop = useCallback(() => {
    if (!activePhraseId || !recorderRef.current) return;
    void finishRecording(activePhraseId, recorderRef.current);
  }, [activePhraseId, finishRecording]);

  const retry = useCallback(
    (phraseId: string) => {
      stopTimer();
      recorderRef.current?.cancel();
      recorderRef.current = null;
      setActivePhraseId(null);
      setClip(phraseId, {
        status: 'idle',
        durationMs: null,
        quality: undefined,
        error: undefined,
      });
    },
    [setClip, stopTimer],
  );

  const reset = useCallback(() => {
    stopTimer();
    recorderRef.current?.cancel();
    recorderRef.current = null;
    setActivePhraseId(null);
    setClips(createInitialClips());
  }, [stopTimer]);

  const completedCount = useMemo(
    () => clips.filter((clip) => clip.status === 'recorded').length,
    [clips],
  );

  const submit = useCallback(
    async (displayName: string) => {
      setFinishing(true);
      try {
        return await completeEnrollment(displayName, clips);
      } finally {
        setFinishing(false);
      }
    },
    [clips, completeEnrollment],
  );

  return {
    phrases: ENROLLMENT_PHRASES,
    clips,
    activePhraseId,
    isRecording: activePhraseId !== null,
    completedCount,
    total: ENROLLMENT_PHRASES.length,
    allComplete: completedCount === ENROLLMENT_PHRASES.length,
    finishing,
    start,
    stop,
    retry,
    reset,
    submit,
  };
}
