import { encodeBase64 } from '@/lib/base64';
import {
  BackendError,
  createRemoteEnrollment,
  deleteRemoteProfile,
  ensureDeviceSession,
  requestVoiceChallenge,
  verifyRemoteVoice,
} from '@/lib/voiceApiClient';
import { clearDeviceSession } from '@/lib/deviceSession';

const DEVICE_RESPONSE = {
  owner_id: 'owner-1',
  device_id: 'device-1',
  access_token: 'token-abc',
};

function mockFetch(
  handler: (url: string, init: RequestInit) => {
    status: number;
    body?: unknown;
    headers?: Record<string, string>;
  },
) {
  const calls: { url: string; init: RequestInit }[] = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const requestInit = init ?? {};
    calls.push({ url, init: requestInit });
    const result = handler(url, requestInit);
    return {
      ok: result.status >= 200 && result.status < 300,
      status: result.status,
      json: async () => result.body ?? {},
      headers: new Headers(result.headers),
    } as unknown as Response;
  }) as unknown as typeof fetch;
  return calls;
}

beforeEach(async () => {
  await clearDeviceSession();
  const secureStore = require('expo-secure-store');
  secureStore.__reset?.();
  delete process.env.EXPO_PUBLIC_CHILL_API_URL;
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('ensureDeviceSession', () => {
  it('registers a device once and reuses the stored token', async () => {
    const calls = mockFetch(() => ({ status: 201, body: DEVICE_RESPONSE }));

    const first = await ensureDeviceSession('test');
    const second = await ensureDeviceSession('test');

    expect(first).toBe('token-abc');
    expect(second).toBe('token-abc');
    expect(calls).toHaveLength(1);
  });
});

describe('requestVoiceChallenge', () => {
  it('returns the phrase the speaker must say', async () => {
    mockFetch((url) =>
      url.endsWith('/v1/devices')
        ? { status: 201, body: DEVICE_RESPONSE }
        : { status: 200, body: { challenge_id: 'challenge-1', phrase: 'alpha bravo' } },
    );

    const challenge = await requestVoiceChallenge();
    expect(challenge.challengeId).toBe('challenge-1');
    expect(challenge.phrase).toBe('alpha bravo');
  });

  it('returns a null phrase when spoken challenges are disabled', async () => {
    mockFetch((url) =>
      url.endsWith('/v1/devices')
        ? { status: 201, body: DEVICE_RESPONSE }
        : { status: 200, body: { challenge_id: 'challenge-1' } },
    );

    const challenge = await requestVoiceChallenge();
    expect(challenge.phrase).toBeNull();
  });
});

describe('verifyRemoteVoice', () => {
  it('maps a backend success into the app result shape', async () => {
    const calls = mockFetch(() =>
      ({
        status: 200,
        body: {
          outcome: 'success',
          reason: 'matched',
          attempts_remaining: 2,
          locked_out: false,
        },
      }),
    );

    const result = await verifyRemoteVoice('AAAA', 2200, 'challenge-1');
    expect(result.outcome).toBe('success');
    expect(result.attemptsRemaining).toBe(2);

    // The caller-supplied challenge id is sent with the sample.
    const verifyCall = calls.find((call) => call.url.endsWith('/v1/verification'));
    const body = JSON.parse(String(verifyCall?.init.body));
    expect(body.challenge_id).toBe('challenge-1');
    expect(verifyCall?.init.method).toBe('POST');
  });

  it('reports a lockout through the reason text', async () => {
    mockFetch(() => ({
      status: 429,
      body: {
        error: {
          code: 'LOCKED_OUT',
          message: 'Too many failed attempts.',
        },
      },
    }));

    await expect(
      verifyRemoteVoice('AAAA', 2200, 'challenge-1'),
    ).rejects.toBeInstanceOf(BackendError);
  });

  it('surfaces the backend error code and status', async () => {
    mockFetch(() => ({
      status: 403,
      body: { error: { code: 'CONSENT_REQUIRED', message: 'Consent required.' } },
    }));

    await expect(
      verifyRemoteVoice('AAAA', 2200, 'challenge-1'),
    ).rejects.toMatchObject({
      code: 'CONSENT_REQUIRED',
      status: 403,
    });
  });
});

describe('enrollment and deletion payloads', () => {
  it('sends enrollment samples under the documented field names', async () => {
    const calls = mockFetch(() => ({ status: 200, body: {} }));

    await createRemoteEnrollment(
      [
        {
          phraseId: 'phrase-1',
          durationMs: 2200,
          quality: 0.9,
          audioBase64: 'AAAA',
        },
      ],
      'Sri',
    );

    const enrollmentCall = calls.find((call) => call.url.endsWith('/v1/enrollment'));
    expect(enrollmentCall).toBeDefined();
    const body = JSON.parse(String(enrollmentCall?.init.body));
    expect(body.display_name).toBe('Sri');
    expect(body.samples[0]).toMatchObject({
      phrase_id: 'phrase-1',
      duration_ms: 2200,
      quality: 0.9,
      audio_base64: 'AAAA',
    });
  });

  it('requires an explicit confirmation to delete the profile', async () => {
    const calls = mockFetch((url) =>
      url.endsWith('/v1/devices') ? { status: 201, body: DEVICE_RESPONSE } : { status: 200, body: {} },
    );
    await ensureDeviceSession('test');

    await deleteRemoteProfile();

    const deleteCall = calls.find((call) => call.url.endsWith('/v1/profile'));
    expect(deleteCall?.init.method).toBe('DELETE');
    expect(JSON.parse(String(deleteCall?.init.body))).toEqual({ confirm: 'DELETE' });
  });
});

describe('encodeBase64', () => {
  it('encodes bytes the same way a standard encoder does', () => {
    // "Hi" -> "SGk=", three bytes -> no padding, one byte -> two '='.
    expect(encodeBase64(new Uint8Array([72, 105]))).toBe('SGk=');
    expect(encodeBase64(new Uint8Array([1, 2, 3]))).toBe('AQID');
    expect(encodeBase64(new Uint8Array([255]))).toBe('/w==');
    expect(encodeBase64(new Uint8Array([]))).toBe('');
  });
});
