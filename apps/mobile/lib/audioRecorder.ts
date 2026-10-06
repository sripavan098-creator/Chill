/**
 * Real audio recording, built on expo-audio.
 *
 * Privacy rules for v0.2:
 * - A recording is written to a temporary cache file.
 * - The file is deleted as soon as mock processing finishes.
 * - Raw audio is never persisted, uploaded, or read back into the app.
 */

import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
} from 'expo-audio';
import type { AudioRecorder } from 'expo-audio';
import { File } from 'expo-file-system';

import { MicrophonePermissionStatus } from '@/types';

export interface CapturedRecording {
  /** Temporary file URI. Deleted by `discardRecording`. */
  uri: string | null;
  durationMs: number;
  /** Signal quality between 0 and 1, derived from duration in v0.2. */
  quality: number;
}

export interface RecordingHandle {
  stop(): Promise<CapturedRecording>;
  cancel(): Promise<void>;
}

/**
 * Maps an expo-audio permission response to the app's tri-state.
 */
export function toPermissionStatus(
  granted: boolean,
  canAskAgain: boolean,
): MicrophonePermissionStatus {
  if (granted) return 'granted';
  return canAskAgain ? 'undetermined' : 'denied';
}

export async function getMicrophonePermission(): Promise<MicrophonePermissionStatus> {
  const response = await AudioModule.getRecordingPermissionsAsync();
  return toPermissionStatus(response.granted, response.canAskAgain);
}

export async function requestMicrophonePermission(): Promise<MicrophonePermissionStatus> {
  const response = await AudioModule.requestRecordingPermissionsAsync();
  return toPermissionStatus(response.granted, response.canAskAgain);
}

/**
 * Opens the audio session for recording. Safe to call repeatedly.
 */
export async function prepareAudioSession(): Promise<void> {
  await setAudioModeAsync({
    allowsRecording: true,
    playsInSilentMode: true,
  });
}

/**
 * Starts a recording session. The caller must stop or cancel it.
 */
export async function startRecording(): Promise<RecordingHandle> {
  await prepareAudioSession();

  // `AudioRecorder` is a property of the `AudioModule` native module instance,
  // which the static import resolver cannot see.
  // eslint-disable-next-line import/namespace
  const recorder: AudioRecorder = new AudioModule.AudioRecorder(
    RecordingPresets.HIGH_QUALITY,
  );
  await recorder.prepareToRecordAsync();
  recorder.record();

  const startedAt = Date.now();

  return {
    async stop() {
      await recorder.stop();
      // Prefer the recorder's own clock; fall back to wall time on platforms
      // that do not report `currentTime` (for example web).
      const reportedSeconds = recorder.currentTime;
      const durationMs =
        reportedSeconds > 0 ? Math.round(reportedSeconds * 1000) : Date.now() - startedAt;
      const uri = recorder.uri;
      recorder.release?.();
      return {
        uri,
        durationMs,
        quality: estimateQuality(durationMs),
      };
    },
    async cancel() {
      try {
        if (recorder.isRecording) {
          await recorder.stop();
        }
      } catch {
        // A recorder that never started cannot be stopped; nothing to clean up.
      }
      const uri = recorder.uri;
      recorder.release?.();
      await discardRecording(uri);
    },
  };
}

/**
 * Deletes a temporary recording. Called after mock processing so no raw
 * audio survives on the device.
 */
export async function discardRecording(uri: string | null): Promise<void> {
  if (!uri) return;
  try {
    const file = new File(uri);
    if (file.exists) {
      file.delete();
    }
  } catch {
    // Best effort: the cache directory is cleared by the OS regardless.
  }
}

/**
 * v0.2 has no acoustic model, so quality is approximated from how long the
 * speaker held the phrase. Milestone 4 replaces this with a real score.
 */
function estimateQuality(durationMs: number): number {
  const seconds = durationMs / 1000;
  if (seconds <= 2) return 0.7;
  if (seconds <= 5) return 0.9;
  return 0.8;
}
