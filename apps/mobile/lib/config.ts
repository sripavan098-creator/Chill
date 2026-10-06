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
