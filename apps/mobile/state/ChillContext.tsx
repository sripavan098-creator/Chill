import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  createVoiceProfile,
  deleteVoiceProfile as deleteVoiceProfileApi,
  getConsent,
  getVoiceProfile,
  recordConsent,
  withdrawConsent,
} from '@/lib/api';
import { STORAGE_KEYS, readJson, storage, writeJson } from '@/lib/storage';
import type { RemoteEnrollmentSample } from '@/lib/voiceApiClient';
import {
  ChillSettings,
  ConsentRecord,
  EnrollmentClip,
  VerificationOutcome,
  VoiceProfile,
} from '@/types';

interface ChillState {
  hydrated: boolean;
  consent: ConsentRecord | null;
  voiceProfile: VoiceProfile | null;
  onboardingComplete: boolean;
  settings: ChillSettings;
}

interface ChillContextValue extends ChillState {
  grantConsent: () => Promise<void>;
  revokeConsent: () => Promise<void>;
  completeEnrollment: (
    displayName: string,
    clips: EnrollmentClip[],
    samples?: RemoteEnrollmentSample[],
  ) => Promise<VoiceProfile>;
  deleteVoiceProfile: () => Promise<void>;
  setSimulateOutcome: (outcome: VerificationOutcome) => Promise<void>;
  resetOnboarding: () => Promise<void>;
}

const DEFAULT_SETTINGS: ChillSettings = { simulateOutcome: 'success' };

const ChillContext = createContext<ChillContextValue | null>(null);

export function ChillProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<ChillState>({
    hydrated: false,
    consent: null,
    voiceProfile: null,
    onboardingComplete: false,
    settings: DEFAULT_SETTINGS,
  });

  useEffect(() => {
    let active = true;

    (async () => {
      const [consent, voiceProfile, complete, settings] = await Promise.all([
        getConsent(),
        getVoiceProfile(),
        readJson<boolean>(STORAGE_KEYS.onboardingComplete),
        readJson<ChillSettings>(STORAGE_KEYS.settings),
      ]);

      if (!active) return;
      setState({
        hydrated: true,
        consent,
        voiceProfile,
        onboardingComplete: Boolean(complete),
        settings: settings ?? DEFAULT_SETTINGS,
      });
    })();

    return () => {
      active = false;
    };
  }, []);

  const grantConsent = useCallback(async () => {
    const consent = await recordConsent(true);
    setState((prev) => ({ ...prev, consent }));
  }, []);

  const revokeConsent = useCallback(async () => {
    await withdrawConsent();
    const consent = await getConsent();
    setState((prev) => ({ ...prev, consent }));
  }, []);

  const completeEnrollment = useCallback(
    async (
      displayName: string,
      clips: EnrollmentClip[],
      samples: RemoteEnrollmentSample[] = [],
    ) => {
      const voiceProfile = await createVoiceProfile(displayName, clips, samples);
      await writeJson(STORAGE_KEYS.onboardingComplete, true);
      setState((prev) => ({
        ...prev,
        voiceProfile,
        onboardingComplete: true,
      }));
      return voiceProfile;
    },
    [],
  );

  const deleteVoiceProfile = useCallback(async () => {
    await deleteVoiceProfileApi();
    await storage.removeItem(STORAGE_KEYS.onboardingComplete);
    setState((prev) => ({
      ...prev,
      voiceProfile: null,
      onboardingComplete: false,
    }));
  }, []);

  const setSimulateOutcome = useCallback(async (outcome: VerificationOutcome) => {
    const settings: ChillSettings = { simulateOutcome: outcome };
    await writeJson(STORAGE_KEYS.settings, settings);
    setState((prev) => ({ ...prev, settings }));
  }, []);

  const resetOnboarding = useCallback(async () => {
    await storage.clear();
    setState({
      hydrated: true,
      consent: null,
      voiceProfile: null,
      onboardingComplete: false,
      settings: DEFAULT_SETTINGS,
    });
  }, []);

  const value = useMemo<ChillContextValue>(
    () => ({
      ...state,
      grantConsent,
      revokeConsent,
      completeEnrollment,
      deleteVoiceProfile,
      setSimulateOutcome,
      resetOnboarding,
    }),
    [
      state,
      grantConsent,
      revokeConsent,
      completeEnrollment,
      deleteVoiceProfile,
      setSimulateOutcome,
      resetOnboarding,
    ],
  );

  return <ChillContext.Provider value={value}>{children}</ChillContext.Provider>;
}

export function useChill(): ChillContextValue {
  const context = useContext(ChillContext);
  if (!context) {
    throw new Error('useChill must be used inside a ChillProvider.');
  }
  return context;
}
