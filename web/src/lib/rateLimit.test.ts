import { describe, it, expect, beforeEach, vi } from "vitest";
import { checkRateLimit } from "./rateLimit";

// Access the private store via the module's closure by re-importing fresh each test
// We mock Date.now to control the sliding window.

describe("checkRateLimit", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Reset module state between tests by re-importing (vitest isolates modules per file, not per test).
    // Use a unique IP per test instead.
  });

  it("allows requests under the limit", () => {
    const result = checkRateLimit("test-ip-allow-1");
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBeGreaterThan(0);
  });

  it("blocks after exceeding 20 requests within the window", () => {
    const ip = "test-ip-exhaust-1";
    for (let i = 0; i < 20; i++) {
      const r = checkRateLimit(ip);
      expect(r.allowed).toBe(true);
    }
    const blocked = checkRateLimit(ip);
    expect(blocked.allowed).toBe(false);
    expect(blocked.remaining).toBe(0);
    expect(blocked.resetInSeconds).toBeGreaterThan(0);
  });

  it("counts remaining correctly", () => {
    const ip = "test-ip-remaining-1";
    const first = checkRateLimit(ip);
    expect(first.remaining).toBe(19); // 20 max - 1 used
    const second = checkRateLimit(ip);
    expect(second.remaining).toBe(18);
  });

  it("treats different IPs independently", () => {
    const ipA = "test-ip-iso-a";
    const ipB = "test-ip-iso-b";
    for (let i = 0; i < 20; i++) checkRateLimit(ipA);
    const blockedA = checkRateLimit(ipA);
    const allowedB = checkRateLimit(ipB);
    expect(blockedA.allowed).toBe(false);
    expect(allowedB.allowed).toBe(true);
  });
});
