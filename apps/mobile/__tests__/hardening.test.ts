import {
  checkAppVersion,
  deleteAccount,
  getConsent,
  getVoiceProfile,
  recordConsent,
  sendFeedback,
} from '@/lib/api';
import { STORAGE_KEYS, storage, writeJson } from '@/lib/storage';

jest.setTimeout(20000);

beforeEach(async () => {
  await storage.clear();
});

describe('deleteAccount', () => {
  it('clears every persisted record, not just the voice profile', async () => {
    await recordConsent(true);
    await writeJson(STORAGE_KEYS.enrollment, { voiceEnrolled: true });
    await writeJson(STORAGE_KEYS.ownerName, 'Sri');
    await writeJson(STORAGE_KEYS.settings, { simulateOutcome: 'success' });
    await writeJson(STORAGE_KEYS.onboardingComplete, true);

    await deleteAccount();

    const remaining = await Promise.all([
      storage.getItem(STORAGE_KEYS.consent),
      storage.getItem(STORAGE_KEYS.enrollment),
      storage.getItem(STORAGE_KEYS.ownerName),
      storage.getItem(STORAGE_KEYS.settings),
      storage.getItem(STORAGE_KEYS.onboardingComplete),
    ]);
    expect(remaining.every((value) => value === null)).toBe(true);
    expect(await getConsent()).toBeNull();
    expect(await getVoiceProfile()).toBeNull();
  });
});

describe('sendFeedback', () => {
  it('resolves in local-only mode without a backend', async () => {
    await expect(sendFeedback('privacy', 'Please clarify retention.', 'ios')).resolves.toBeUndefined();
  });
});

describe('checkAppVersion', () => {
  it('fails open to an unknown verdict without a backend', async () => {
    const verdict = await checkAppVersion();
    expect(verdict.status).toBe('unknown');
  });
});