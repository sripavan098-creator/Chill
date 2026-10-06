import {
  MAX_RECORDING_MS,
  MIN_RECORDING_MS,
  TOO_LONG_MESSAGE,
  TOO_SHORT_MESSAGE,
  isDurationAcceptable,
  validateDuration,
} from '@/features/voice-auth/validation';

describe('validateDuration', () => {
  it('accepts a duration inside the allowed window', () => {
    const result = validateDuration(3000);
    expect(result.verdict).toBe('ok');
    expect(result.message).toBeNull();
    expect(result.durationMs).toBe(3000);
  });

  it('accepts the exact boundaries', () => {
    expect(validateDuration(MIN_RECORDING_MS).verdict).toBe('ok');
    expect(validateDuration(MAX_RECORDING_MS).verdict).toBe('ok');
  });

  it('rejects a recording that is too short', () => {
    const result = validateDuration(MIN_RECORDING_MS - 1);
    expect(result.verdict).toBe('too-short');
    expect(result.message).toBe(TOO_SHORT_MESSAGE);
    expect(result.message).toBe('Please speak a little longer.');
  });

  it('rejects a recording that is too long and clamps the duration', () => {
    const result = validateDuration(MAX_RECORDING_MS + 5000);
    expect(result.verdict).toBe('too-long');
    expect(result.message).toBe(TOO_LONG_MESSAGE);
    expect(result.durationMs).toBe(MAX_RECORDING_MS);
  });

  it('treats a zero-length recording as too short', () => {
    expect(validateDuration(0).verdict).toBe('too-short');
  });
});

describe('isDurationAcceptable', () => {
  it.each([1500, 4000, 8000])('accepts %ims', (ms) => {
    expect(isDurationAcceptable(ms)).toBe(true);
  });

  it.each([0, 1499, 8001])('rejects %ims', (ms) => {
    expect(isDurationAcceptable(ms)).toBe(false);
  });
});
