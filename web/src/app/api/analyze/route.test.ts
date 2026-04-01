import { describe, it, expect } from "vitest";

// ---------------------------------------------------------------------------
// Validation logic extracted for unit testing (mirrors route.ts constants)
// ---------------------------------------------------------------------------

const MAX_BYTES = 4 * 1024 * 1024;
const VALID_MEDIA_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"] as const;
type ValidMediaType = (typeof VALID_MEDIA_TYPES)[number];

function validateRequest(imageBase64: unknown, mediaType: unknown) {
  if (
    typeof imageBase64 !== "string" || !imageBase64 ||
    !VALID_MEDIA_TYPES.includes(mediaType as ValidMediaType)
  ) {
    return { ok: false, status: 400, error: "imageBase64 (string) and valid mediaType are required" };
  }
  const decodedBytes = Math.floor((imageBase64 as string).length * 0.75);
  if (decodedBytes > MAX_BYTES) {
    return { ok: false, status: 413, error: "Image too large. Maximum size is ~3 MB." };
  }
  return { ok: true };
}

describe("analyze route — request validation", () => {
  it("accepts a valid small request", () => {
    const result = validateRequest("abc123==", "image/png");
    expect(result.ok).toBe(true);
  });

  it("rejects missing imageBase64", () => {
    const result = validateRequest("", "image/png");
    expect(result.ok).toBe(false);
    expect(result.status).toBe(400);
  });

  it("rejects invalid mediaType", () => {
    const result = validateRequest("abc123==", "image/bmp");
    expect(result.ok).toBe(false);
    expect(result.status).toBe(400);
  });

  it("rejects all valid media types would pass", () => {
    for (const mt of VALID_MEDIA_TYPES) {
      expect(validateRequest("abc123==", mt).ok).toBe(true);
    }
  });

  it("rejects oversized payload", () => {
    // ~4 MB of base64 characters → decoded ~3 MB → just over limit
    const oversized = "A".repeat(Math.ceil((MAX_BYTES + 1) / 0.75));
    const result = validateRequest(oversized, "image/png");
    expect(result.ok).toBe(false);
    expect(result.status).toBe(413);
  });

  it("accepts payload right at the limit", () => {
    // exactly MAX_BYTES decoded
    const atLimit = "A".repeat(Math.ceil(MAX_BYTES / 0.75));
    const result = validateRequest(atLimit, "image/png");
    expect(result.ok).toBe(true);
  });
});
