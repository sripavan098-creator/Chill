/**
 * Runtime configuration.
 *
 * The backend is opt-in. Until `EXPO_PUBLIC_CHILL_API_URL` is set, the app runs
 * in local-only mode and no data leaves the device. Setting it points the voice
 * features at the FastAPI service from milestone 3.
 */

export const API_BASE_URL = (process.env.EXPO_PUBLIC_CHILL_API_URL ?? '').replace(
  /\/+$/,
  '',
);

/**
 * True when a backend is configured. The API client falls back to local
 * storage otherwise, so the onboarding flow still works offline.
 */
export const USE_REMOTE_API = API_BASE_URL.length > 0;

/** Request timeout for backend calls, in milliseconds. */
export const REQUEST_TIMEOUT_MS = 10000;

/**
 * Public links surfaced in the app. Kept here so a real privacy policy or
 * support page can replace them without touching screens. The in-app legal
 * screen summarises these principles; the links lead to the full documents.
 */
export const PRIVACY_URL =
  'https://github.com/sripavan098-creator/Chill/blob/main/docs/PRIVACY.md';
export const SECURITY_URL =
  'https://github.com/sripavan098-creator/Chill/blob/main/docs/SECURITY.md';
export const REPO_URL = 'https://github.com/sripavan098-creator/Chill';
