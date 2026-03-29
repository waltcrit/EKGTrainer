// In-memory rate limiter using a sliding window.
// Good for single-instance deployments (Vercel free tier, local dev).
// For multi-instance production, swap the Map for Upstash Redis:
// https://github.com/upstash/ratelimit-js

const WINDOW_MS = 60 * 60 * 1000; // 1 hour
const MAX_REQUESTS = 20;           // per IP per hour

// Map of IP → array of request timestamps within the current window
const store = new Map<string, number[]>();

// Prevent unbounded memory growth — purge IPs with no recent activity
let lastCleanup = Date.now();
const CLEANUP_INTERVAL_MS = 10 * 60 * 1000; // every 10 minutes

function cleanup() {
  const now = Date.now();
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

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetInSeconds: number;
}

export function checkRateLimit(ip: string): RateLimitResult {
  cleanup();

  const now = Date.now();
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
}
