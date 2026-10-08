/**
 * End-to-end smoke tests for the Chill v0.5 user journey.
 *
 * These drive the real Expo Router app (screens + hooks + mock services) the
 * way a person would: tapping labelled controls and reading on-screen text.
 * Native audio, file system and storage are faked in `jest.setup.ts`, so the
 * whole onboarding, sign-in and settings flow runs in Node.
 *
 * Two RNTL v14 / expo-router quirks shape this file:
 * - `render` is async and `renderRouter` returns its promise, so every render
 *   is awaited. The route helpers live on that promise, so `renderApp` returns
 *   it inside an object to stop `await` from unwrapping them.
 * - `renderRouter` switches Jest to fake timers. The mock API resolves on
 *   `setTimeout`, so we restore real timers right after the first render or
 *   every await hangs.
 * `screen` is imported from `@testing-library/react-native`; the re-export
 * from expo-router snapshots the unpopulated placeholder.
 */

import {
  act,
  cleanup,
  fireEvent,
  screen,
  waitFor,
} from '@testing-library/react-native';
import { renderRouter } from 'expo-router/testing-library';

import { STORAGE_KEYS, storage } from '@/lib/storage';
import type {
  ChillSettings,
  ConsentRecord,
  EnrollmentMetadata,
} from '@/types';
import {
  audioMockState,
  resetAudioMockState,
} from '@/test/mocks/audioMockState';

jest.setTimeout(60000);

type App = ReturnType<typeof renderRouter>;

async function renderApp(initialUrl = '/'): Promise<{ app: App }> {
  const app = renderRouter('app', { initialUrl });
  await app;
  jest.useRealTimers();
  return { app };
}

/** Fire a press inside `act` so React flushes the resulting state update. */
async function press(label: string | RegExp, index = 0) {
  await act(async () => {
    fireEvent.press(screen.getAllByLabelText(label)[index]);
  });
}

async function writeJson(key: string, value: unknown) {
  await storage.setItem(key, JSON.stringify(value));
}

/** Persists a fully enrolled owner so downstream screens load with a profile. */
async function seedEnrolledOwner(
  options: { simulate?: ChillSettings['simulateOutcome']; displayName?: string } = {},
) {
  const consent: ConsentRecord = {
    granted: true,
    grantedAt: new Date().toISOString(),
    policyVersion: '2026-10-01',
  };
  const enrollment: EnrollmentMetadata = {
    voiceEnrolled: true,
    consentGranted: true,
    enrollmentCompletedAt: new Date().toISOString(),
    enrollmentVersion: '0.2.0',
  };
  await writeJson(STORAGE_KEYS.consent, consent);
  await writeJson(STORAGE_KEYS.enrollment, enrollment);
  await writeJson(STORAGE_KEYS.ownerName, options.displayName ?? 'Sri');
  await writeJson(STORAGE_KEYS.onboardingComplete, true);
  if (options.simulate) {
    await writeJson(STORAGE_KEYS.settings, { simulateOutcome: options.simulate });
  }
}

beforeEach(async () => {
  // Unmount any tree from a previous test so expo-router's "linking configured
  // in multiple places" warning does not fire.
  cleanup();
  resetAudioMockState();
  await storage.clear();
});

describe('Chill end-to-end journey', () => {
  it('cold start lands on the welcome screen', async () => {
    const { app } = await renderApp('/');

    expect(app.getPathname()).toBe('/welcome');
    expect(screen.getByText(/Welcome to Chill/)).toBeTruthy();
    expect(screen.getByText(/Recognizes you by voice/)).toBeTruthy();
  });

  it('walks welcome → microphone permission → consent', async () => {
    const { app } = await renderApp('/welcome');

    await press('Get started');
    await waitFor(() => expect(app.getPathname()).toBe('/permissions'));
    expect(screen.getByText('Microphone access')).toBeTruthy();

    // The fake OS reports the microphone as granted, so this continues.
    await press('Allow microphone');
    await waitFor(() => expect(app.getPathname()).toBe('/consent'));
    expect(screen.getByText('Voice consent')).toBeTruthy();

    // Consent is gated: the primary button stays disabled until every box is on.
    const agree = screen.getByLabelText('Agree and continue');
    expect(agree.props.accessibilityState.disabled).toBe(true);

    await press(/I consent to Chill processing my voice/);
    await press(/I understand that raw recordings are not stored/);
    await press(/I understand that I can delete my voice profile/);

    await waitFor(() =>
      expect(
        screen.getByLabelText('Agree and continue').props.accessibilityState
          .disabled,
      ).toBe(false),
    );

    await press('Agree and continue');
    await waitFor(() => expect(app.getPathname()).toBe('/enroll'));
  });

  it('records all five phrases, creates the profile and stores no raw audio', async () => {
    audioMockState.recordingDurationMs = 3000;
    // Enrollment requires an existing consent record.
    await writeJson(STORAGE_KEYS.consent, {
      granted: true,
      grantedAt: new Date().toISOString(),
      policyVersion: '2026-10-01',
    });

    const { app } = await renderApp('/enroll');
    expect(screen.getByText('Voice enrollment')).toBeTruthy();
    expect(screen.getByText(/0 of 5 phrases captured/)).toBeTruthy();

    for (let index = 0; index < 5; index += 1) {
      await press('Record phrase');
      await waitFor(
        () => expect(screen.getAllByLabelText('Stop recording').length).toBe(1),
        { timeout: 8000 },
      );
      await press('Stop recording');
      // Each take waits on the 1s mock processing step before it is counted.
      await waitFor(
        () =>
          expect(
            screen.getByText(new RegExp(`${index + 1} of 5 phrases captured`)),
          ).toBeTruthy(),
        { timeout: 8000 },
      );
    }

    // Finish is only enabled once all five samples are captured.
    await waitFor(() =>
      expect(
        screen.getByLabelText('Create my voice profile').props
          .accessibilityState.disabled,
      ).toBe(false),
    );
    await press('Create my voice profile');

    await waitFor(() => expect(app.getPathname()).toBe('/enroll-success'), {
      timeout: 10000,
    });
    expect(screen.getByText('You are enrolled')).toBeTruthy();

    // Privacy invariant: each temp recording was deleted, and nothing
    // biometric was written to storage.
    expect(audioMockState.deletedFiles).toHaveLength(5);
    const stored = await Promise.all([
      storage.getItem(STORAGE_KEYS.enrollment),
      storage.getItem(STORAGE_KEYS.ownerName),
      storage.getItem(STORAGE_KEYS.consent),
      storage.getItem(STORAGE_KEYS.onboardingComplete),
    ]);
    expect(stored.join(' ')).not.toMatch(/\.m4a|\.wav|base64/i);
  });

  it('signs in with a successful mock voice match and reaches home', async () => {
    audioMockState.recordingDurationMs = 3000;
    await seedEnrolledOwner({ simulate: 'success' });

    const { app } = await renderApp('/login');
    expect(screen.getByText('Voice sign-in')).toBeTruthy();

    await press('Start voice verification');

    // The login recorder auto-stops at its limit, then the mock model runs.
    await waitFor(() => expect(app.getPathname()).toBe('/home'), {
      timeout: 20000,
    });
    expect(screen.getByText('Hi, Sri')).toBeTruthy();
  });

  it('shows a spoken challenge phrase before recording a login sample', async () => {
    audioMockState.recordingDurationMs = 3000;
    await seedEnrolledOwner({ simulate: 'success' });

    await renderApp('/login');
    expect(screen.queryByText('Say this phrase')).toBeNull();

    await press('Start voice verification');

    // A fresh phrase is fetched and read before the sample is checked.
    await waitFor(() => expect(screen.getByText('Say this phrase')).toBeTruthy(), {
      timeout: 20000,
    });
    expect(screen.getByText(/Hey Chill, your code is /)).toBeTruthy();
  });

  it('falls back to PIN when the mock voice match fails, then continues home', async () => {
    audioMockState.recordingDurationMs = 3000;
    await seedEnrolledOwner({ simulate: 'failure' });

    const { app } = await renderApp('/login');
    await press('Start voice verification');

    await waitFor(() => expect(screen.getByText('No match')).toBeTruthy(), {
      timeout: 20000,
    });
    expect(app.getPathname()).toBe('/login');

    await press('Use PIN instead');
    await waitFor(() => expect(app.getPathname()).toBe('/fallback'));
    expect(screen.getByText('Use your PIN')).toBeTruthy();

    expect(
      screen.getByLabelText('Continue to home').props.accessibilityState.disabled,
    ).toBe(true);

    await act(async () => {
      fireEvent.changeText(screen.getByLabelText('PIN'), '1234');
    });
    await waitFor(() =>
      expect(
        screen.getByLabelText('Continue to home').props.accessibilityState
          .disabled,
      ).toBe(false),
    );

    await press('Continue to home');
    await waitFor(() => expect(app.getPathname()).toBe('/home'));
  });

  it('deletes the voice profile from settings behind a confirmation', async () => {
    await seedEnrolledOwner();

    const { app } = await renderApp('/settings');
    expect(screen.getByText('Settings')).toBeTruthy();
    expect(screen.getByText('Enrolled')).toBeTruthy();

    await press('Delete voice profile');
    await waitFor(() =>
      expect(screen.getByText('Delete voice profile?')).toBeTruthy(),
    );

    await press('Delete');

    await waitFor(() => expect(app.getPathname()).toBe('/welcome'), {
      timeout: 10000,
    });
    expect(await storage.getItem(STORAGE_KEYS.enrollment)).toBeNull();
    expect(await storage.getItem(STORAGE_KEYS.onboardingComplete)).toBeNull();
  });

  it('keeps every route reachable without crashing (smoke)', async () => {
    await seedEnrolledOwner();

    for (const route of ['/', '/welcome', '/permissions', '/consent', '/enroll']) {
      const { app } = await renderApp(route);
      expect(app.getPathname()).toBeTruthy();
      await cleanup();
    }

    const { app } = await renderApp('/home');
    expect(screen.getByText(/Hi, Sri/)).toBeTruthy();
  });
});
