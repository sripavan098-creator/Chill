/**
 * Network resilience helpers.
 *
 * `withRetry` wraps a call that may fail transiently (a flaky connection, a
 * short server hiccup) and retries it a few times with backoff. It is only for
 * idempotent work: verification attempts and consent writes are not retried by
 * default, because a retry could double-charge a rate limit or re-record.
 */

export interface RetryOptions {
  attempts?: number;
  /** Base delay in milliseconds; doubles each try. */
  baseDelayMs?: number;
  /** Return false to stop retrying immediately. */
  shouldRetry?: (error: unknown) => boolean;
  onRetry?: (attempt: number, error: unknown) => void;
}

const DEFAULT_ATTEMPTS = 3;
const DEFAULT_BASE_DELAY_MS = 400;

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Runs `task`, retrying transient failures with linear-ish backoff. */
export async function withRetry<T>(
  task: () => Promise<T>,
  options: RetryOptions = {},
): Promise<T> {
  const attempts = options.attempts ?? DEFAULT_ATTEMPTS;
  const baseDelayMs = options.baseDelayMs ?? DEFAULT_BASE_DELAY_MS;

  let lastError: unknown;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await task();
    } catch (error) {
      lastError = error;
      const retryable = options.shouldRetry ? options.shouldRetry(error) : true;
      if (!retryable || attempt === attempts) break;
      options.onRetry?.(attempt, error);
      await delay(baseDelayMs * attempt);
    }
  }
  throw lastError;
}

/** Distinguishes likely-transient errors from permanent ones. */
export function isRetryableError(error: unknown): boolean {
  if (error instanceof TypeError) return true; // fetch/network failure
  const status = (error as { status?: number })?.status;
  if (typeof status === 'number') {
    return status >= 500 || status === 429;
  }
  const code = (error as { code?: string })?.code;
  return code === 'REQUEST_FAILED' || code === 'NETWORK_ERROR';
}