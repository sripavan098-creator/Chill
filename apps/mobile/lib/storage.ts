/**
 * Mock key/value storage.
 *
 * v0.1 keeps everything in memory so no biometric data touches the device.
 * Milestone 2 swaps this for expo-secure-store behind the same interface.
 */

export interface StorageAdapter {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
  clear(): Promise<void>;
}

export const STORAGE_KEYS = {
  consent: 'chill.consent',
  voiceProfile: 'chill.voiceProfile',
  settings: 'chill.settings',
  onboardingComplete: 'chill.onboardingComplete',
} as const;

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

class InMemoryStorage implements StorageAdapter {
  private store = new Map<string, string>();

  async getItem(key: string): Promise<string | null> {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  async setItem(key: string, value: string): Promise<void> {
    this.store.set(key, value);
  }

  async removeItem(key: string): Promise<void> {
    this.store.delete(key);
  }

  async clear(): Promise<void> {
    this.store.clear();
  }
}

export const storage: StorageAdapter = new InMemoryStorage();

export async function readJson<T>(key: string): Promise<T | null> {
  const raw = await storage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    // Corrupt mock payloads should not crash onboarding.
    await storage.removeItem(key);
    return null;
  }
}

export async function writeJson<T>(key: string, value: T): Promise<void> {
  await storage.setItem(key, JSON.stringify(value));
}
