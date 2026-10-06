import { createInitialClips } from '@/features/voice-auth/phrases';
import {
  createVoiceProfile,
  deleteVoiceProfile,
  getVoiceProfile,
  recordConsent,
  verifyVoice,
} from '@/lib/api';
import { STORAGE_KEYS, storage } from '@/lib/storage';

jest.setTimeout(20000);

beforeEach(async () => {
  await storage.clear();
});

function completedClips() {
  return createInitialClips().map((clip) => ({
    ...clip,
    status: 'recorded' as const,
    durationMs: 3000,
    quality: 0.9,
  }));
}

describe('createVoiceProfile', () => {
  it('requires consent', async () => {
    await expect(createVoiceProfile('Sri', completedClips())).rejects.toThrow(
      /consent/i,
    );
  });

  it('requires five recorded samples', async () => {
    await recordConsent(true);
    const partial = completedClips().slice(0, 4);
    await expect(createVoiceProfile('Sri', partial)).rejects.toThrow(/five/i);
  });

  it('stores enrollment metadata and the owner name', async () => {
    await recordConsent(true);
    const profile = await createVoiceProfile('  Sri  ', completedClips());

    expect(profile.displayName).toBe('Sri');
    expect(profile.phraseCount).toBe(5);

    const metadata = await storage.getItem(STORAGE_KEYS.enrollment);
    expect(metadata).toContain('"voiceEnrolled":true');
  });
});

describe('getVoiceProfile', () => {
  it('returns null before enrollment', async () => {
    expect(await getVoiceProfile()).toBeNull();
  });

  it('rebuilds the profile from metadata after enrollment', async () => {
    await recordConsent(true);
    await createVoiceProfile('Sri', completedClips());

    const profile = await getVoiceProfile();
    expect(profile?.displayName).toBe('Sri');
  });
});

describe('deleteVoiceProfile', () => {
  it('clears the profile and enrollment metadata', async () => {
    await recordConsent(true);
    await createVoiceProfile('Sri', completedClips());
    expect(await getVoiceProfile()).not.toBeNull();

    await deleteVoiceProfile();

    expect(await getVoiceProfile()).toBeNull();
    expect(await storage.getItem(STORAGE_KEYS.enrollment)).toBeNull();
    expect(await storage.getItem(STORAGE_KEYS.ownerName)).toBeNull();
  });
});

describe('verifyVoice', () => {
  it('refuses to verify without an enrolled profile', async () => {
    await expect(verifyVoice('success', 1)).rejects.toThrow(/no voice profile/i);
  });

  it('honours the forced failure outcome from the developer toggle', async () => {
    await recordConsent(true);
    await createVoiceProfile('Sri', completedClips());

    const result = await verifyVoice('failure', 1);
    expect(result.outcome).toBe('failure');
    expect(result.attemptsRemaining).toBe(2);
  });
});
