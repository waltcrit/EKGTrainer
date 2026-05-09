/**
 * P2 — Sliding-window limiter behavior with injected clock.
 */
import { describe, it, expect } from "vitest";
import { createRateLimiter } from "@/lib/rateLimit";

describe("createRateLimiter", () => {
  it("allows requests under max and blocks with remaining=0 when exceeded", () => {
    let t = 1_000_000;
    const limiter = createRateLimiter({
      windowMs: 3600_000,
      maxRequests: 3,
      now: () => t,
      cleanupIntervalMs: 999_999_999,
    });

    expect(limiter("1.1.1.1")).toEqual({ allowed: true, remaining: 2, resetInSeconds: 0 });
    expect(limiter("1.1.1.1")).toEqual({ allowed: true, remaining: 1, resetInSeconds: 0 });
    expect(limiter("1.1.1.1")).toEqual({ allowed: true, remaining: 0, resetInSeconds: 0 });

    const blocked = limiter("1.1.1.1");
    expect(blocked.allowed).toBe(false);
    expect(blocked.remaining).toBe(0);
    expect(blocked.resetInSeconds).toBeGreaterThan(0);

    expect(limiter("2.2.2.2")).toEqual({ allowed: true, remaining: 2, resetInSeconds: 0 });
  });

  it("opens again after the window slides past the oldest stamp", () => {
    let t = 10_000;
    const limiter = createRateLimiter({
      windowMs: 1000,
      maxRequests: 2,
      now: () => t,
      cleanupIntervalMs: 999_999_999,
    });

    expect(limiter("ip")).toEqual({ allowed: true, remaining: 1, resetInSeconds: 0 });
    expect(limiter("ip")).toEqual({ allowed: true, remaining: 0, resetInSeconds: 0 });
    expect(limiter("ip").allowed).toBe(false);

    t += 1001;
    expect(limiter("ip").allowed).toBe(true);
  });
});
