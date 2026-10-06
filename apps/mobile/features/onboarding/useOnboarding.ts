import { useCallback } from 'react';

import { CONSENT_POLICY_VERSION } from '@/lib/api';
import { useChill } from '@/state/ChillContext';

/**
 * Consent flow for the onboarding stack.
 *
 * v0.1 stores consent as a local mock record. Milestone 3 moves this to the
 * backend so consent can be audited server-side.
 */
export function useOnboarding() {
  const { consent, grantConsent, revokeConsent } = useChill();

  const grant = useCallback(async () => {
    await grantConsent();
  }, [grantConsent]);

  const withdraw = useCallback(async () => {
    await revokeConsent();
  }, [revokeConsent]);

  return {
    consent,
    policyVersion: CONSENT_POLICY_VERSION,
    grant,
    withdraw,
  };
}
