import { act, renderHook, waitFor } from '@testing-library/react-native';
import React from 'react';

import { useEnrollment } from '@/features/voice-auth/useEnrollment';
import { recordConsent } from '@/lib/api';
import { STORAGE_KEYS, storage } from '@/lib/storage';
import { ChillProvider } from '@/state/ChillContext';
import {
  audioMockState,
  resetAudioMockState,
} from '@/test/mocks/audioMockState';

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <ChillProvider>{children}</ChillProvider>
);

// Each enrollment sample waits on the simulated processing delay (1s) plus the
// simulated profile creation (0.9s), so the full flow needs a longer budget.
jest.setTimeout(30000);

beforeEach(async () => {
  resetAudioMockState();
  await storage.clear();
});

async function recordEveryPhrase(result: { current: ReturnType<typeof useEnrollment> }) {
  for (const phrase of result.current.phrases) {
    await act(async () => {
      await result.current.start(phrase.id);
    });
    await act(async () => {
      await result.current.stop();
    });
  }
}

describe('useEnrollment', () => {
  it('starts with every phrase idle and nothing complete', async () => {
    const { result } = await renderHook(() => useEnrollment(), { wrapper });

    expect(result.current.total).toBe(5);
    expect(result.current.completedCount).toBe(0);
    expect(result.current.allComplete).toBe(false);
    expect(result.current.clips.every((clip) => clip.status === 'idle')).toBe(true);
  });

  it('marks a phrase recorded and advances the progress after a valid take', async () => {
    audioMockState.recordingDurationMs = 3000;
    const { result } = await renderHook(() => useEnrollment(), { wrapper });

    const first = result.current.phrases[0];
    await act(async () => {
      await result.current.start(first.id);
    });
    await act(async () => {
      await result.current.stop();
    });

    await waitFor(() => expect(result.current.completedCount).toBe(1));
    const clip = result.current.clips.find((item) => item.phraseId === first.id);
    expect(clip?.status).toBe('recorded');
    expect(clip?.durationMs).toBe(3000);

    // No raw audio is retained on the clip.
    expect(clip).not.toHaveProperty('uri');
  });

  it('exposes a recording state while a phrase is being captured', async () => {
    const { result } = await renderHook(() => useEnrollment(), { wrapper });
    const first = result.current.phrases[0];

    await act(async () => {
      await result.current.start(first.id);
    });

    // The screen relies on this to show the timer and a stop control.
    expect(
      result.current.clips.find((item) => item.phraseId === first.id)?.status,
    ).toBe('recording');

    await act(async () => {
      await result.current.stop();
    });
    await waitFor(() => expect(result.current.completedCount).toBe(1));
  });

  it('records a too-short take as an error and keeps it out of the count', async () => {
    audioMockState.recordingDurationMs = 400;
    const { result } = await renderHook(() => useEnrollment(), { wrapper });

    const first = result.current.phrases[0];
    await act(async () => {
      await result.current.start(first.id);
    });
    await act(async () => {
      await result.current.stop();
    });

    await waitFor(() =>
      expect(
        result.current.clips.find((item) => item.phraseId === first.id)?.status,
      ).toBe('error'),
    );
    expect(result.current.completedCount).toBe(0);
    expect(result.current.allComplete).toBe(false);
  });

  it('allows a failed phrase to be retried', async () => {
    audioMockState.recordingDurationMs = 400;
    const { result } = await renderHook(() => useEnrollment(), { wrapper });
    const first = result.current.phrases[0];

    await act(async () => {
      await result.current.start(first.id);
    });
    await act(async () => {
      await result.current.stop();
    });
    await waitFor(() =>
      expect(
        result.current.clips.find((item) => item.phraseId === first.id)?.status,
      ).toBe('error'),
    );

    audioMockState.recordingDurationMs = 3000;
    await act(async () => {
      await result.current.retry(first.id);
    });
    await act(async () => {
      await result.current.start(first.id);
    });
    await act(async () => {
      await result.current.stop();
    });

    await waitFor(() => expect(result.current.completedCount).toBe(1));
  });

  it('persists enrollment metadata but never raw audio', async () => {
    audioMockState.recordingDurationMs = 3000;
    await recordConsent(true);

    const { result } = await renderHook(() => useEnrollment(), { wrapper });
    await recordEveryPhrase(result);
    await waitFor(() => expect(result.current.allComplete).toBe(true));

    await act(async () => {
      await result.current.submit('Sri');
    });

    const keys = await storage.getItem(STORAGE_KEYS.enrollment);
    expect(keys).toContain('"voiceEnrolled":true');

    const name = await storage.getItem(STORAGE_KEYS.ownerName);
    expect(name).toBe('"Sri"');

    // Every temporary recording was deleted, and no stored value holds audio.
    expect(audioMockState.deletedFiles).toHaveLength(5);
    const all = await Promise.all([
      storage.getItem(STORAGE_KEYS.enrollment),
      storage.getItem(STORAGE_KEYS.ownerName),
      storage.getItem(STORAGE_KEYS.consent),
    ]);
    expect(all.join(' ')).not.toMatch(/\.m4a|\.wav|base64/);
  });

  it('refuses to create a profile when consent is missing', async () => {
    audioMockState.recordingDurationMs = 3000;
    const { result } = await renderHook(() => useEnrollment(), { wrapper });
    await recordEveryPhrase(result);
    await waitFor(() => expect(result.current.allComplete).toBe(true));

    await expect(
      act(async () => {
        await result.current.submit('Sri');
      }),
    ).rejects.toThrow(/consent/i);
  });
});
