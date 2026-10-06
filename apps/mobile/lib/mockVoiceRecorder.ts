/**
 * Mock audio recorder.
 *
 * v0.1 never opens the microphone. This module only simulates start/stop,
 * duration and a fake quality score so the UI can be built and tested.
 * Milestone 2 replaces it with expo-av / react-native-audio-recorder-player.
 */

import { ClipStatus } from '@/types';

export interface RecordingSession {
  status: ClipStatus;
  /** Mock elapsed time in milliseconds. */
  durationMs: number;
  /** Mock signal quality between 0 and 1. */
  quality: number;
}

export interface MockRecorderHandle {
  session: RecordingSession;
  /** Advances the mock clock. Returns the updated session. */
  tick(elapsedMs: number): RecordingSession;
  /** Stops the mock recording and resolves with the final session. */
  stop(): Promise<RecordingSession>;
  /** Aborts without producing a usable clip. */
  cancel(): void;
}

const MIN_USABLE_DURATION_MS = 800;
const MAX_MOCK_DURATION_MS = 4000;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function randomBetween(min: number, max: number): number {
  return Math.round(min + Math.random() * (max - min));
}

export function createMockRecorder(): MockRecorderHandle {
  let session: RecordingSession = {
    status: 'recording',
    durationMs: 0,
    quality: 0,
  };

  return {
    get session() {
      return session;
    },
    tick(elapsedMs: number) {
      session = {
        ...session,
        durationMs: Math.min(elapsedMs, MAX_MOCK_DURATION_MS),
      };
      return session;
    },
    async stop() {
      session = {
        status: session.durationMs >= MIN_USABLE_DURATION_MS ? 'recorded' : 'error',
        durationMs: session.durationMs,
        quality:
          session.durationMs >= MIN_USABLE_DURATION_MS
            ? randomBetween(80, 99) / 100
            : 0,
      };
      await delay(150);
      return session;
    },
    cancel() {
      session = { status: 'idle', durationMs: 0, quality: 0 };
    },
  };
}

/**
 * Simulates listening for a voice login attempt.
 * Resolves with a mock similarity score after a short delay.
 */
export async function simulateListen(listenMs = 2000): Promise<{ similarity: number }> {
  await delay(listenMs);
  return { similarity: randomBetween(60, 99) / 100 };
}

export function isUsableClip(session: RecordingSession): boolean {
  return session.status === 'recorded' && session.durationMs >= MIN_USABLE_DURATION_MS;
}

export { MAX_MOCK_DURATION_MS, MIN_USABLE_DURATION_MS };
