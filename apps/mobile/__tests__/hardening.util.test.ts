import {
  CALIBRATION,
  gradeSample,
} from '@/lib/calibration';
import {
  compareVersions,
  evaluateVersionPolicy,
  parseVersion,
} from '@/lib/appVersion';
import { isRetryableError, withRetry } from '@/lib/retry';

describe('gradeSample', () => {
  it('flags a too-short clip regardless of quality', () => {
    const result = gradeSample(CALIBRATION.minDurationMs - 1, 1);
    expect(result.band).toBe('weak');
    expect(result.shouldRetry).toBe(true);
  });

  it('flags a poor-quality clip for retry', () => {
    const result = gradeSample(CALIBRATION.idealDurationMs, 0.1);
    expect(result.band).toBe('weak');
    expect(result.shouldRetry).toBe(true);
  });

  it('calls a long, clean clip strong', () => {
    const result = gradeSample(CALIBRATION.idealDurationMs, 0.9);
    expect(result.band).toBe('strong');
    expect(result.shouldRetry).toBe(false);
  });

  it('treats an acceptable mid-range clip as good', () => {
    const result = gradeSample(CALIBRATION.minDurationMs, 0.6);
    expect(result.band).toBe('good');
    expect(result.shouldRetry).toBe(false);
  });
});

describe('version comparison', () => {
  it('parses prefixes and suffixes', () => {
    expect(parseVersion('v1.2.3-beta.1')).toEqual({ major: 1, minor: 2, patch: 3 });
  });

  it('orders versions correctly', () => {
    expect(compareVersions('0.2.0', '0.2.1')).toBe(-1);
    expect(compareVersions('1.0.0', '0.9.9')).toBe(1);
    expect(compareVersions('0.2.0', '0.2.0')).toBe(0);
  });
});

describe('evaluateVersionPolicy', () => {
  const policy = {
    minimum_supported: '0.2.0',
    latest: '0.3.0',
    update_url: 'https://example.com/update',
  };

  it('requires an update below the minimum', () => {
    expect(evaluateVersionPolicy(policy, '0.1.0').status).toBe('update-required');
  });

  it('recommends an update below latest but above minimum', () => {
    expect(evaluateVersionPolicy(policy, '0.2.5').status).toBe('update-recommended');
  });

  it('is ok at or above latest', () => {
    expect(evaluateVersionPolicy(policy, '0.3.0').status).toBe('ok');
  });
});

describe('withRetry', () => {
  it('retries transient failures and then succeeds', async () => {
    let calls = 0;
    const value = await withRetry(async () => {
      calls += 1;
      if (calls < 3) throw new TypeError('network');
      return 'ok';
    });
    expect(value).toBe('ok');
    expect(calls).toBe(3);
  });

  it('stops when shouldRetry returns false', async () => {
    let calls = 0;
    await expect(
      withRetry(
        async () => {
          calls += 1;
          throw Object.assign(new Error('bad request'), { status: 400 });
        },
        { shouldRetry: (error) => isRetryableError(error) },
      ),
    ).rejects.toThrow('bad request');
    expect(calls).toBe(1);
  });
});

describe('isRetryableError', () => {
  it('treats 5xx and 429 as retryable', () => {
    expect(isRetryableError({ status: 503 })).toBe(true);
    expect(isRetryableError({ status: 429 })).toBe(true);
  });

  it('treats 4xx client errors as permanent', () => {
    expect(isRetryableError({ status: 400 })).toBe(false);
  });
});