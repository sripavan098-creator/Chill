/**
 * Controllable state shared with the native module mocks in `jest.setup.ts`.
 *
 * Jest forbids out-of-scope variables in `jest.mock` factories, so the state
 * lives in its own module that both the factory and the tests import.
 */

export interface MockPermissionState {
  granted: boolean;
  canAskAgain: boolean;
}

export const audioMockState = {
  permission: { granted: true, canAskAgain: true } as MockPermissionState,
  /** Duration reported by the fake recorder's stop(), in milliseconds. */
  recordingDurationMs: 3000,
  /** URIs passed to File.delete(), so tests can prove temp cleanup happened. */
  deletedFiles: [] as string[],
  recordingUri: 'file:///tmp/chill-test.m4a',
  /** When set, the fake recorder rejects on start. */
  failOnStart: false,
  permissionThrows: false,
};

export function resetAudioMockState() {
  audioMockState.permission = { granted: true, canAskAgain: true };
  audioMockState.recordingDurationMs = 3000;
  audioMockState.deletedFiles = [];
  audioMockState.recordingUri = 'file:///tmp/chill-test.m4a';
  audioMockState.failOnStart = false;
  audioMockState.permissionThrows = false;
}
