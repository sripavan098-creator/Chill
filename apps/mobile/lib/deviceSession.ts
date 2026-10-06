/**
 * Device access token storage.
 *
 * The token is a bearer credential, so it goes in the platform secure store
 * (Keychain / Keystore) rather than AsyncStorage. When secure storage is not
 * available, the token is held in memory only: the app re-registers on next
 * launch instead of writing a credential somewhere less protected.
 */

import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'chill.deviceToken';
const OWNER_KEY = 'chill.ownerId';
const DEVICE_KEY = 'chill.deviceId';

let memoryToken: string | null = null;

async function isAvailable(): Promise<boolean> {
  try {
    return await SecureStore.isAvailableAsync();
  } catch {
    return false;
  }
}

export async function saveDeviceSession(session: {
  accessToken: string;
  ownerId: string;
  deviceId: string;
}): Promise<void> {
  memoryToken = session.accessToken;
  if (!(await isAvailable())) return;
  await SecureStore.setItemAsync(TOKEN_KEY, session.accessToken);
  await SecureStore.setItemAsync(OWNER_KEY, session.ownerId);
  await SecureStore.setItemAsync(DEVICE_KEY, session.deviceId);
}

export async function getAccessToken(): Promise<string | null> {
  if (memoryToken) return memoryToken;
  if (!(await isAvailable())) return null;
  const token = await SecureStore.getItemAsync(TOKEN_KEY);
  memoryToken = token;
  return token;
}

export async function clearDeviceSession(): Promise<void> {
  memoryToken = null;
  if (!(await isAvailable())) return;
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(OWNER_KEY);
  await SecureStore.deleteItemAsync(DEVICE_KEY);
}
