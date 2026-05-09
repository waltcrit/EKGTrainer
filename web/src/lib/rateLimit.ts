// In-memory rate limiter using a sliding window.
// Good for single-instance deployments (Vercel free tier, local dev).
// For multi-instance production, swap the Map for Upstash Redis:
// https://github.com/upstash/ratelimit-js

export interface RateLimiterOptions {
  windowMs: number;
  maxRequests: number;
  /** Wall clock — inject in tests for deterministic behavior */
  now?: () => number;
  cleanupIntervalMs?: number;
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetInSeconds: number;
}

export type CheckRateLimit = (ip: string) => RateLimitResult;

export function createRateLimiter(options: RateLimiterOptions): CheckRateLimit {
  const WINDOW_MS = options.windowMs;
  const MAX_REQUESTS = options.maxRequests;
  const nowFn = options.now ?? Date.now;
  const CLEANUP_INTERVAL_MS = options.cleanupIntervalMs ?? 10 * 60 * 1000;

  const store = new Map<string, number[]>();
  let lastCleanup = nowFn();

  function cleanup() {
    const now = nowFn();
    if (now - lastCleanup < CLEANUP_INTERVAL_MS) return;
    lastCleanup = now;
    const cutoff = now - WINDOW_MS;
    for (const [ip, timestamps] of store.entries()) {
      const recent = timestamps.filter((t) => t > cutoff);
      if (recent.length === 0) {
        store.delete(ip);
      } else {
        store.set(ip, recent);
      }
    }
  }

  return function checkRateLimit(ip: string): RateLimitResult {
    cleanup();

    const now = nowFn();
    const cutoff = now - WINDOW_MS;
    const timestamps = (store.get(ip) ?? []).filter((t) => t > cutoff);

    if (timestamps.length >= MAX_REQUESTS) {
      const oldest = timestamps[0];
      const resetInSeconds = Math.ceil((oldest + WINDOW_MS - now) / 1000);
      return { allowed: false, remaining: 0, resetInSeconds };
    }

    timestamps.push(now);
    store.set(ip, timestamps);

    return {
      allowed: true,
      remaining: MAX_REQUESTS - timestamps.length,
      resetInSeconds: 0,
    };
  };
}

const WINDOW_MS = 60 * 60 * 1000; // 1 hour
const MAX_REQUESTS = 20;           // per IP per hour

/** Production limiter for `/api/analyze`. */
export const checkRateLimit = createRateLimiter({
  windowMs: WINDOW_MS,
  maxRequests: MAX_REQUESTS,
});
