/**
 * Jest setup.
 *
 * Native audio, file system and key/value modules are mocked so the recording
 * flow can be exercised in Node. Test files adjust behaviour through
 * `test/mocks/audioMockState`.
 *
 * `require` is used inside the `jest.mock` factories because Jest forbids
 * referencing out-of-scope variables there.
 */
/* eslint-disable @typescript-eslint/no-require-imports */

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

jest.mock('expo-audio', () => {
  const state = require('@/test/mocks/audioMockState').audioMockState;

  const AudioRecorder = jest.fn().mockImplementation(() => {
    const instance = {
      uri: state.recordingUri,
      isRecording: false,
      currentTime: state.recordingDurationMs / 1000,
      prepareToRecordAsync: jest.fn(() =>
        state.failOnStart
          ? Promise.reject(new Error('microphone unavailable'))
          : Promise.resolve(undefined),
      ),
      record: jest.fn(),
      stop: jest.fn().mockResolvedValue(undefined),
      release: jest.fn(),
    };
    return instance;
  });

  const permissionResponse = () => ({
    ...state.permission,
    status: state.permission.granted ? 'granted' : 'denied',
  });

  return {
    AudioModule: {
      AudioRecorder,
      getRecordingPermissionsAsync: jest.fn(() =>
        state.permissionThrows
          ? Promise.reject(new Error('permission unavailable'))
          : Promise.resolve(permissionResponse()),
      ),
      requestRecordingPermissionsAsync: jest.fn(() =>
        state.permissionThrows
          ? Promise.reject(new Error('permission unavailable'))
          : Promise.resolve(permissionResponse()),
      ),
    },
    RecordingPresets: { HIGH_QUALITY: {}, LOW_QUALITY: {} },
    setAudioModeAsync: jest.fn().mockResolvedValue(undefined),
  };
});

jest.mock('expo-file-system', () => {
  const state = require('@/test/mocks/audioMockState').audioMockState;

  return {
    File: jest.fn().mockImplementation((uri: string) => ({
      uri,
      exists: true,
      delete: jest.fn(() => {
        state.deletedFiles.push(uri);
      }),
    })),
  };
});
