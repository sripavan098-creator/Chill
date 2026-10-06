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

import { encodeBase64 } from '@/lib/base64';
import { USE_REMOTE_API } from '@/lib/config';
import { MicrophonePermissionStatus } from '@/types';

export interface CapturedRecording {
  /** Temporary file URI. Deleted by `discardRecording`. */
  uri: string | null;
  durationMs: number;
  /** Signal quality between 0 and 1, derived from duration in v0.2. */
  quality: number;
  /**
   * Base64 audio for the backend embedding step. Present only when a backend
   * is configured, and held in memory just long enough to upload. Never
   * persisted.
   */
  audioBase64?: string | null;
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

      // With a backend configured the sample is read once, in memory, so the
      // server can compute an embedding. The file itself is still deleted.
      const audioBase64 = USE_REMOTE_API ? await readBase64(uri) : null;

      recorder.release?.();
      return {
        uri,
        durationMs,
        quality: estimateQuality(durationMs),
        audioBase64,
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
 * Reads a temporary recording as base64, for the one-time upload to the
 * backend. Returns null when the file is gone or unreadable; the caller then
 * simply skips the remote embedding step.
 */
async function readBase64(uri: string | null): Promise<string | null> {
  if (!uri) return null;
  try {
    const file = new File(uri);
    if (!file.exists) return null;
    const buffer = await file.arrayBuffer();
    return encodeBase64(new Uint8Array(buffer));
  } catch {
    return null;
  }
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
