import { useCallback, useMemo, useRef, useState } from 'react';

import { ENROLLMENT_PHRASES, createInitialClips } from '@/features/voice-auth/phrases';
import { RecorderOutcome, useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import type { RemoteEnrollmentSample } from '@/lib/voiceApiClient';
import { useChill } from '@/state/ChillContext';
import { EnrollmentClip } from '@/types';

/**
 * Drives the real enrollment recording flow.
 *
 * Each phrase is recorded through `useVoiceRecorder`, which deletes the
 * temporary file before reporting an outcome. Only clip status, duration and
 * quality are kept in state, so the screen stays presentational and no raw
 * audio survives.
 */
export function useEnrollment() {
  const { completeEnrollment } = useChill();
  const [clips, setClips] = useState<EnrollmentClip[]>(() => createInitialClips());
  const [activePhraseId, setActivePhraseId] = useState<string | null>(null);
  const [finishing, setFinishing] = useState(false);

  const activePhraseRef = useRef<string | null>(null);
  // Audio for the backend embedding step, held in memory only and dropped as
  // soon as enrollment finishes. Empty when no backend is configured.
  const samplesRef = useRef<Map<string, RemoteEnrollmentSample>>(new Map());

  const setClip = useCallback((phraseId: string, patch: Partial<EnrollmentClip>) => {
    setClips((prev) =>
      prev.map((clip) => (clip.phraseId === phraseId ? { ...clip, ...patch } : clip)),
    );
  }, []);

  // Recording outcomes arrive from the recorder, including auto-stopped takes.
  const handleOutcome = useCallback(
    (outcome: RecorderOutcome) => {
      const phraseId = activePhraseRef.current;
      if (!phraseId) return;

      if (outcome.status === 'success') {
        if (outcome.captured.audioBase64) {
          samplesRef.current.set(phraseId, {
            phraseId,
            durationMs: outcome.captured.durationMs,
            quality: outcome.captured.quality,
            audioBase64: outcome.captured.audioBase64,
          });
        }
        setClip(phraseId, {
          status: 'recorded',
          durationMs: outcome.captured.durationMs,
          quality: outcome.captured.quality,
          error: undefined,
        });
      } else {
        samplesRef.current.delete(phraseId);
        setClip(phraseId, {
          status: 'error',
          durationMs: null,
          quality: 0,
          error: outcome.error ?? 'Could not record. Please try again.',
        });
      }

      activePhraseRef.current = null;
      setActivePhraseId(null);
    },
    [setClip],
  );

  const recorder = useVoiceRecorder({ onOutcome: handleOutcome });
  const { reset: resetRecorder } = recorder;

  // Drop the previous take before recording the same phrase again.
  const preparePhrase = useCallback(
    (phraseId: string) => {
      resetRecorder();
      samplesRef.current.delete(phraseId);
      setClip(phraseId, {
        status: 'idle',
        durationMs: null,
        quality: undefined,
        error: undefined,
      });
    },
    [resetRecorder, setClip],
  );

  const start = useCallback(
    async (phraseId: string) => {
      if (recorder.isActive) return;
      preparePhrase(phraseId);
      activePhraseRef.current = phraseId;
      setActivePhraseId(phraseId);
      setClip(phraseId, { status: 'preparing' });
      await recorder.start();
    },
    [preparePhrase, recorder, setClip],
  );

  const stop = useCallback(async () => {
    await recorder.stop();
  }, [recorder]);

  const retry = useCallback(
    async (phraseId: string) => {
      await recorder.cancel();
      activePhraseRef.current = null;
      setActivePhraseId(null);
      preparePhrase(phraseId);
    },
    [preparePhrase, recorder],
  );

  const reset = useCallback(async () => {
    await recorder.cancel();
    activePhraseRef.current = null;
    setActivePhraseId(null);
    samplesRef.current.clear();
    setClips(createInitialClips());
  }, [recorder]);

  const completedCount = useMemo(
    () => clips.filter((clip) => clip.status === 'recorded').length,
    [clips],
  );

  const submit = useCallback(
    async (displayName: string) => {
      setFinishing(true);
      try {
        const samples = ENROLLMENT_PHRASES.map((phrase) =>
          samplesRef.current.get(phrase.id),
        ).filter((sample): sample is RemoteEnrollmentSample => Boolean(sample));
        return await completeEnrollment(displayName, clips, samples);
      } finally {
        // The audio is only needed until the profile is created.
        samplesRef.current.clear();
        setFinishing(false);
      }
    },
    [clips, completeEnrollment],
  );

  return {
    phrases: ENROLLMENT_PHRASES,
    clips,
    activePhraseId,
    elapsedMs: recorder.elapsedMs,
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
