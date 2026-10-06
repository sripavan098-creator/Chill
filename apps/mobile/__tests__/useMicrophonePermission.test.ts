import { act, renderHook, waitFor } from '@testing-library/react-native';

import { useMicrophonePermission } from '@/hooks/useMicrophonePermission';
import {
  audioMockState,
  resetAudioMockState,
} from '@/test/mocks/audioMockState';

beforeEach(() => {
  resetAudioMockState();
});

describe('useMicrophonePermission', () => {
  it('reports granted access after the automatic check', async () => {
    const { result } = await renderHook(() => useMicrophonePermission());

    await waitFor(() => expect(result.current.checking).toBe(false));
    expect(result.current.status).toBe('granted');
    expect(result.current.granted).toBe(true);
  });

  it('reports denied access when the OS refuses', async () => {
    audioMockState.permission = { granted: false, canAskAgain: false };
    const { result } = await renderHook(() => useMicrophonePermission());

    await waitFor(() => expect(result.current.status).toBe('denied'));
    expect(result.current.denied).toBe(true);
  });

  it('requests access and returns the resulting status', async () => {
    audioMockState.permission = { granted: false, canAskAgain: true };
    const { result } = await renderHook(() => useMicrophonePermission());

    // `canAskAgain` is true, so the OS prompt is still available.
    await waitFor(() => expect(result.current.status).toBe('undetermined'));

    audioMockState.permission = { granted: true, canAskAgain: true };
    let next: string | undefined;
    await act(async () => {
      next = await result.current.request();
    });

    expect(next).toBe('granted');
    expect(result.current.granted).toBe(true);
  });

  it('surfaces a friendly error when the permission API fails', async () => {
    audioMockState.permissionThrows = true;
    const { result } = await renderHook(() => useMicrophonePermission());

    await waitFor(() => expect(result.current.checking).toBe(false));
    expect(result.current.error).toMatch(/could not read the microphone permission/);
  });
});
