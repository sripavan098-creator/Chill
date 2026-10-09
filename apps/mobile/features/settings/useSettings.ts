import { useCallback, useState } from 'react';

import { useMicrophonePermission } from '@/hooks/useMicrophonePermission';
import { APP_VERSION } from '@/lib/appVersion';
import { useChill } from '@/state/ChillContext';

/**
 * Settings actions.
 *
 * Both destructive paths are gated behind an explicit confirmation in the
 * screen before they run. `eraseAccount` is the heavier of the two: it also
 * clears the backend owner and the stored device token.
 */
export function useSettings() {
  const {
    voiceProfile,
    consent,
    settings,
    version,
    deleteVoiceProfile,
    deleteAccount,
    revokeConsent,
    resetOnboarding,
    setSimulateOutcome,
  } = useChill();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const microphone = useMicrophonePermission();

  const run = useCallback(async (action: () => Promise<void>, failure: string) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      return true;
    } catch {
      setError(failure);
      return false;
    } finally {
      setBusy(false);
    }
  }, []);

  const deleteProfile = useCallback(
    () =>
      run(
        () => deleteVoiceProfile(),
        'We could not delete your voice profile. Please try again.',
      ),
    [deleteVoiceProfile, run],
  );

  const eraseAccount = useCallback(
    () =>
      run(
        () => deleteAccount(),
        'We could not delete your account. Please try again.',
      ),
    [deleteAccount, run],
  );

  const reset = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await resetOnboarding();
    } finally {
      setBusy(false);
    }
  }, [resetOnboarding]);

  const setSimulateFailure = useCallback(
    (next: boolean) => {
      void setSimulateOutcome(next ? 'failure' : 'success');
    },
    [setSimulateOutcome],
  );

  return {
    voiceProfile,
    consent,
    appVersion: APP_VERSION,
    versionStatus: version?.status ?? 'unknown',
    versionMessage: version?.message ?? '',
    microphoneStatus: microphone.status,
    microphoneGranted: microphone.granted,
    microphoneDenied: microphone.denied,
    openMicrophoneSettings: microphone.openSettings,
    simulateFailure: settings.simulateOutcome === 'failure',
    busy,
    error,
    deleteProfile,
    eraseAccount,
    revokeConsent,
    reset,
    setSimulateFailure,
  };
}
