import { NextRequest, NextResponse } from "next/server";
import { checkRateLimit } from "@/lib/rateLimit";
import { assembleAnalysisResult } from "@/lib/analyzeAssembly";
import type { AnalyzeRequest, AnalyzeResponse, AnalyzeErrorResponse } from "@/types/analysis";
import type { ImageMediaType, Image, PipelineData, PythonServiceResult } from "@/types/pipeline";
import measurementsData from "@/data/measurements.json";

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL ?? "http://localhost:8000";
const PYTHON_API_KEY = process.env.PYTHON_API_KEY ?? "";

// ---------------------------------------------------------------------------
// Step 1 — Acquire pipeline data
//
// Priority order:
//   1. Pre-computed measurements from measurements.json (caseId fast-path)
//   2. Python digitizer service (live signal analysis)
//   3. null — no measurements available
// ---------------------------------------------------------------------------

async function acquirePipelineData(
  image: Image | null,
  caseId: string | undefined,
): Promise<PipelineData | null> {
  if (caseId) {
    const precomputed = (measurementsData as Record<string, PipelineData>)[caseId];
    if (precomputed) return precomputed;
  }
  if (image) return runPythonPipeline(image.base64, image.mediaType);
  return null;
}

async function runPythonPipeline(imageBase64: string, mediaType: string): Promise<PythonServiceResult> {
  let res: Response;
  try {
    res = await fetch(`${PYTHON_SERVICE_URL}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(PYTHON_API_KEY ? { "Authorization": `Bearer ${PYTHON_API_KEY}` } : {}),
      },
      body: JSON.stringify({ image_base64: imageBase64, media_type: mediaType }),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(`Python service unreachable: ${msg}`);
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json() as { detail?: { error?: string } | string };
      if (typeof body.detail === "string") detail = body.detail;
      else if (typeof body.detail?.error === "string") detail = body.detail.error;
    } catch { /* ignore */ }
    throw new Error(`Python pipeline failed: ${detail}`);
  }

  return res.json() as Promise<PythonServiceResult>;
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

const VALID_MEDIA_TYPES: readonly ImageMediaType[] = [
  "image/jpeg", "image/png", "image/gif", "image/webp",
];
const MAX_BYTES = 4 * 1024 * 1024;

export async function POST(
  req: NextRequest,
): Promise<NextResponse<AnalyzeResponse | AnalyzeErrorResponse>> {
  const ip =
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ??
    req.headers.get("x-real-ip") ??
    "unknown";

  const rate = checkRateLimit(ip);
  if (!rate.allowed) {
    return NextResponse.json(
      { success: false, error: `Rate limit reached. Try again in ${rate.resetInSeconds} seconds.` },
      { status: 429, headers: { "Retry-After": String(rate.resetInSeconds) } },
    );
  }

  const contentLength = Number(req.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BYTES) {
    return NextResponse.json(
      { success: false, error: "Request too large. Maximum image size is ~3 MB." },
      { status: 413 },
    );
  }

  let body: AnalyzeRequest;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ success: false, error: "Invalid request body" }, { status: 400 });
  }

  const { imageBase64, mediaType, caseId } = body;

  let image: Image | null = null;
  if (imageBase64 || mediaType) {
    if (
      typeof imageBase64 !== "string" || !imageBase64 ||
      !VALID_MEDIA_TYPES.includes(mediaType as ImageMediaType)
    ) {
      return NextResponse.json(
        { success: false, error: "imageBase64 (string) and valid mediaType are required" },
        { status: 400 },
      );
    }
    const decodedBytes = Math.floor(imageBase64.length * 0.75);
    if (decodedBytes > MAX_BYTES) {
      return NextResponse.json(
        { success: false, error: "Image too large. Maximum size is ~3 MB." },
        { status: 413 },
      );
    }
    image = { base64: imageBase64, mediaType: mediaType as ImageMediaType };
  }

  if (!image && !caseId) {
    return NextResponse.json(
      { success: false, error: "Provide imageBase64 or a known caseId" },
      { status: 400 },
    );
  }

  try {
    const pipelineData = await acquirePipelineData(image, caseId);
    if (!pipelineData) {
      return NextResponse.json(
        { success: false, error: "Signal pipeline data unavailable. Provide a known caseId or enable the Python PhysioNet service." },
        { status: 503 },
      );
    }
    const result = assembleAnalysisResult(pipelineData);
    return NextResponse.json({ success: true, result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
