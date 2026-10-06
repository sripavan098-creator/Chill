import { useCallback, useEffect, useState } from 'react';
import { Linking } from 'react-native';

import {
  getMicrophonePermission,
  requestMicrophonePermission,
} from '@/lib/audioRecorder';
import { MicrophonePermissionStatus } from '@/types';

/**
 * Microphone permission lifecycle.
 *
 * `denied` means the OS will no longer show a prompt, so the UI offers the
 * device settings shortcut instead of re-requesting.
 */
export function useMicrophonePermission(autoCheck = true) {
  const [status, setStatus] = useState<MicrophonePermissionStatus>('undetermined');
  const [checking, setChecking] = useState(autoCheck);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await getMicrophonePermission();
      setStatus(next);
      setError(null);
      return next;
    } catch {
      setError('Chill could not read the microphone permission. Please try again.');
      return 'undetermined' as MicrophonePermissionStatus;
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    if (autoCheck) {
      // Subscribes to the OS permission API on mount. `refresh` only calls
      // setState after awaiting the native call, so this is not a synchronous
      // cascading render.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void refresh();
    }
  }, [autoCheck, refresh]);

  // Manual re-check (for example the "Try again" button) shows the spinner.
  const recheck = useCallback(async () => {
    setChecking(true);
    return refresh();
  }, [refresh]);

  const request = useCallback(async () => {
    setRequesting(true);
    try {
      const next = await requestMicrophonePermission();
      setStatus(next);
      setError(null);
      return next;
    } catch {
      setError('Chill could not request microphone access. Please try again.');
      return 'undetermined' as MicrophonePermissionStatus;
    } finally {
      setRequesting(false);
    }
  }, []);

  const openSettings = useCallback(async () => {
    try {
      await Linking.openSettings();
    } catch {
      setError('Open your device settings and enable microphone access for Chill.');
    }
  }, []);

  return {
    status,
    granted: status === 'granted',
    denied: status === 'denied',
    checking,
    requesting,
    error,
    refresh: recheck,
    request,
    openSettings,
  };
}
