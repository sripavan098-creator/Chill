/**
 * Client version checks.
 *
 * The app compares its own version against the backend's `/v1/version` policy
 * on launch. `minimum_supported` is the oldest version the backend still
 * serves; below it the user is asked to update. Comparison is intentionally
 * simple semver (major.minor.patch); build metadata is ignored.
 */

import Constants from 'expo-constants';

export const APP_VERSION: string =
  Constants.expoConfig?.version ?? '0.0.0';

export interface ParsedVersion {
  major: number;
  minor: number;
  patch: number;
}

export function parseVersion(value: string): ParsedVersion {
  const core = value.trim().replace(/^v/i, '').split(/[-+]/)[0];
  const parts = core.split('.').map((part) => Number.parseInt(part, 10));
  return {
    major: Number.isFinite(parts[0]) ? parts[0] : 0,
    minor: Number.isFinite(parts[1]) ? parts[1] : 0,
    patch: Number.isFinite(parts[2]) ? parts[2] : 0,
  };
}

/** Returns -1, 0 or 1 as `a` is older than, equal to, or newer than `b`. */
export function compareVersions(a: string, b: string): number {
  const left = parseVersion(a);
  const right = parseVersion(b);
  for (const key of ['major', 'minor', 'patch'] as const) {
    if (left[key] !== right[key]) return left[key] < right[key] ? -1 : 1;
  }
  return 0;
}

export type VersionStatus = 'ok' | 'update-recommended' | 'update-required' | 'unknown';

export interface VersionVerdict {
  status: VersionStatus;
  /** Safe to show the user. */
  message: string;
  updateUrl: string | null;
}

interface VersionPolicy {
  minimum_supported: string;
  latest: string;
  update_url: string;
}

/**
 * Applies the backend policy to this build.
 *
 * A failed or malformed response resolves to `unknown`, which is treated as
 * "keep working": a version check must never lock a user out on its own.
 */
export function evaluateVersionPolicy(
  policy: VersionPolicy,
  current: string = APP_VERSION,
): VersionVerdict {
  if (compareVersions(current, policy.minimum_supported) < 0) {
    return {
      status: 'update-required',
      message: 'This version of Chill is no longer supported. Please update to continue.',
      updateUrl: policy.update_url,
    };
  }
  if (compareVersions(current, policy.latest) < 0) {
    return {
      status: 'update-recommended',
      message: 'A newer version of Chill is available with fixes and improvements.',
      updateUrl: policy.update_url,
    };
  }
  return { status: 'ok', message: '', updateUrl: null };
}

export function unknownVerdict(): VersionVerdict {
  return { status: 'unknown', message: '', updateUrl: null };
}