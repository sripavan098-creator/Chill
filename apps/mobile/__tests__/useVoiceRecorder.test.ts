import { act, renderHook, waitFor } from '@testing-library/react-native';

import { MAX_RECORDING_MS } from '@/features/voice-auth/validation';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import {
  audioMockState,
  resetAudioMockState,
} from '@/test/mocks/audioMockState';

beforeEach(() => {
  resetAudioMockState();
});

describe('useVoiceRecorder', () => {
  it('starts idle', async () => {
    const { result } = await renderHook(() => useVoiceRecorder());
    expect(result.current.state).toBe('idle');
    expect(result.current.isActive).toBe(false);
  });

  it('records, processes, deletes the temp file and reports success', async () => {
    audioMockState.recordingDurationMs = 3000;
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    expect(result.current.state).toBe('recording');

    await act(async () => {
      await result.current.stop();
    });

    expect(result.current.state).toBe('success');
    expect(result.current.captured?.durationMs).toBe(3000);
    expect(result.current.captured?.uri).toBeNull();

    // Privacy guarantee: the temporary recording is deleted after processing.
    expect(audioMockState.deletedFiles).toEqual([audioMockState.recordingUri]);
  });

  it('flags a recording that is too short and still deletes the file', async () => {
    audioMockState.recordingDurationMs = 500;
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.stop();
    });

    expect(result.current.state).toBe('error');
    expect(result.current.error).toBe('Please speak a little longer.');
    expect(audioMockState.deletedFiles).toHaveLength(1);
  });

  it('accepts a recording at the maximum length', async () => {
    audioMockState.recordingDurationMs = MAX_RECORDING_MS;
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.stop();
    });

    expect(result.current.state).toBe('success');
  });

  it('surfaces a friendly error when the microphone cannot start', async () => {
    audioMockState.failOnStart = true;
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.state).toBe('error');
    expect(result.current.error).toMatch(/Could not start recording/);
  });

  it('cancels a recording and returns to idle', async () => {
    const { result } = await renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.cancel();
    });

    expect(result.current.state).toBe('idle');
    expect(result.current.isActive).toBe(false);
  });

  it('skips the mock processing step when disabled', async () => {
    const { result } = await renderHook(() => useVoiceRecorder({ processSample: false }));

    await act(async () => {
      await result.current.start();
    });
    await act(async () => {
      await result.current.stop();
    });

    await waitFor(() => expect(result.current.state).toBe('success'));
  });
});
