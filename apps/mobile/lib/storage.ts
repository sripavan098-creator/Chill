/**
 * Device storage.
 *
 * v0.2 persists non-sensitive records (consent, enrollment status, settings)
 * through AsyncStorage. Anything secret would move to SecureStore in a later
 * milestone; nothing biometric is ever written here.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

export interface StorageAdapter {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
  clear(): Promise<void>;
}

export const STORAGE_KEYS = {
  consent: 'chill.consent',
  enrollment: 'chill.enrollment',
  ownerName: 'chill.ownerName',
  settings: 'chill.settings',
  onboardingComplete: 'chill.onboardingComplete',
} as const;

export type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

class AsyncStorageAdapter implements StorageAdapter {
  async getItem(key: string): Promise<string | null> {
    return AsyncStorage.getItem(key);
  }

  async setItem(key: string, value: string): Promise<void> {
    await AsyncStorage.setItem(key, value);
  }

  async removeItem(key: string): Promise<void> {
    await AsyncStorage.removeItem(key);
  }

  async clear(): Promise<void> {
    await AsyncStorage.clear();
  }
}

export const storage: StorageAdapter = new AsyncStorageAdapter();

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
