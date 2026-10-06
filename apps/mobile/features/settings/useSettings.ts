import { useCallback, useState } from 'react';

import { useMicrophonePermission } from '@/hooks/useMicrophonePermission';
import { useChill } from '@/state/ChillContext';

/**
 * Settings actions. Deletion is gated behind an explicit confirmation in the
 * screen before `deleteProfile` runs.
 */
export function useSettings() {
  const {
    voiceProfile,
    consent,
    settings,
    deleteVoiceProfile,
    revokeConsent,
    resetOnboarding,
    setSimulateOutcome,
  } = useChill();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const microphone = useMicrophonePermission();

  const deleteProfile = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteVoiceProfile();
      return true;
    } catch {
      setError('We could not delete your voice profile. Please try again.');
      return false;
    } finally {
      setBusy(false);
    }
  }, [deleteVoiceProfile]);

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
    microphoneStatus: microphone.status,
    microphoneGranted: microphone.granted,
    microphoneDenied: microphone.denied,
    openMicrophoneSettings: microphone.openSettings,
    simulateFailure: settings.simulateOutcome === 'failure',
    busy,
    error,
    deleteProfile,
    revokeConsent,
    reset,
    setSimulateFailure,
  };
}
