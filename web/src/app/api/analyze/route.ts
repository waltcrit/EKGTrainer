import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";
import { checkRateLimit } from "@/lib/rateLimit";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  AnalyzeErrorResponse,
  EKGAnalysisResult,
  PipelineClassification,
} from "@/types/analysis";
import measurementsData from "@/data/measurements.json";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ImageMediaType = "image/jpeg" | "image/png" | "image/gif" | "image/webp";
interface Image { base64: string; mediaType: ImageMediaType }

interface PipelineData {
  measurements: Record<string, unknown>;
  claude_prompt: string;
  digitizer_method: string;
  leads_available: string[];
  sampling_rate: number;
  pipeline_classification?: PipelineClassification | null;
}

interface PythonServiceResult extends PipelineData { success: true }

// ---------------------------------------------------------------------------
// Prompt used when no signal measurements are available (vision-only fallback)
// ---------------------------------------------------------------------------

const VISION_ONLY_PROMPT = `You are an expert cardiologist performing a systematic ECG interpretation. Analyze this ECG image carefully and return ONLY a valid JSON object matching exactly this structure (no markdown, no extra text):

{
  "rate": { "bpm": <number>, "rr_intervals_ms": [<numbers>], "category": "bradycardia"|"normal"|"tachycardia", "method": "visual", "confidence": <0-1> },
  "rhythm": { "regularity": "regular"|"regularly_irregular"|"irregularly_irregular", "confidence": <0-1> },
  "p_waves": { "present": <bool>, "morphology": <string|null>, "ratio": <string|null>, "confidence": <0-1> },
  "pr_interval": { "ms": <number|null>, "measured_beats": [<numbers>], "normal": <bool|null>, "fixed": <bool|null>, "confidence": <0-1> },
  "qrs": { "duration_ms": <number|null>, "measured_beats_ms": [<numbers>], "wide": <bool>, "morphology": <string|null>, "confidence": <0-1> },
  "st_segment": { "elevation": <bool>, "depression": <bool>, "details": <string|null>, "confidence": <0-1> },
  "t_waves": { "morphology": <string|null>, "confidence": <0-1> },
  "qtc": { "ms": <number|null>, "measured_qt_ms": [<numbers>], "prolonged": <bool|null>, "confidence": <0-1> },
  "primary_rhythm": "<string>",
  "overall_confidence": <0-1>,
  "differentials": ["<string>", ...],
  "explanation": "<detailed systematic interpretation>",
  "image_quality": "good"|"fair"|"poor",
  "caveats": "<string|null>"
}

Be systematic: rate → rhythm → axis → P waves → PR → QRS → ST/T → QTc → impression.`;

// ---------------------------------------------------------------------------
// Step 1 — Acquire pipeline data (measurements + Claude prompt)
//
// Strategies in priority order:
//   1. Pre-computed measurements from measurements.json (caseId fast-path)
//   2. Python digitizer service (live signal analysis)
//   3. null — no measurements; Claude will interpret from the image directly
// ---------------------------------------------------------------------------

async function acquirePipelineData(
  image: Image | null,
  caseId: string | undefined,
): Promise<PipelineData | null> {
  if (caseId) {
    const precomputed = (measurementsData as Record<string, PipelineData>)[caseId];
    if (precomputed) {
      console.log(`\n=== CLAUDE PROMPT for caseId=${caseId} ===\n${precomputed.claude_prompt}\n=== END PROMPT ===\n`);
      return precomputed;
    }
  }

  if (image && process.env.PYTHON_SERVICE_URL) {
    return await runPythonPipeline(image.base64, image.mediaType);
  }

  return null;
}

async function runPythonPipeline(imageBase64: string, mediaType: string): Promise<PythonServiceResult> {
  let res: Response;
  try {
    res = await fetch(`${PYTHON_SERVICE_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_base64: imageBase64, media_type: mediaType }),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new Error(`Python service unreachable (${PYTHON_SERVICE_URL}): ${msg}`);
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
// Step 2 — Call Claude
//
// Always sends the image when one is available so Claude has full visual
// context regardless of how measurements were obtained.
// The prompt is measurements-based when pipeline data exists, or the
// generic vision prompt when falling back to image-only analysis.
// ---------------------------------------------------------------------------

async function callClaude(prompt: string, image: Image | null): Promise<EKGAnalysisResult> {
  const content: Anthropic.Messages.MessageParam["content"] = [];
  if (image) {
    content.push({
      type: "image",
      source: { type: "base64", media_type: image.mediaType, data: image.base64 },
    });
  }
  content.push({ type: "text", text: prompt });

  const message = await anthropic.messages.create({
    model: process.env.CLAUDE_MODEL ?? "claude-haiku-4-5-20251001",
    max_tokens: 4096,
    messages: [{ role: "user", content }],
  });

  const responseText = message.content[0].type === "text" ? message.content[0].text : "";
  const cleaned = responseText
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();

  return JSON.parse(cleaned) as EKGAnalysisResult;
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

const VALID_MEDIA_TYPES: readonly ImageMediaType[] = [
  "image/jpeg", "image/png", "image/gif", "image/webp",
];
const MAX_BYTES = 4 * 1024 * 1024; // 4 MB

export async function POST(
  req: NextRequest
): Promise<NextResponse<AnalyzeResponse | AnalyzeErrorResponse>> {
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(
      { success: false, error: "ANTHROPIC_API_KEY is not configured" },
      { status: 500 }
    );
  }

  const ip =
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ??
    req.headers.get("x-real-ip") ??
    "unknown";

  const rate = checkRateLimit(ip);
  if (!rate.allowed) {
    return NextResponse.json(
      { success: false, error: `Rate limit reached. Try again in ${rate.resetInSeconds} seconds.` },
      { status: 429, headers: { "Retry-After": String(rate.resetInSeconds) } }
    );
  }

  const contentLength = Number(req.headers.get("content-length") ?? 0);
  if (contentLength > MAX_BYTES) {
    return NextResponse.json(
      { success: false, error: "Request too large. Maximum image size is ~3 MB." },
      { status: 413 }
    );
  }

  let body: AnalyzeRequest;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ success: false, error: "Invalid request body" }, { status: 400 });
  }

  const { imageBase64, mediaType, caseId } = body;

  // Validate and wrap image (optional — precomputed cases may omit it)
  let image: Image | null = null;
  if (imageBase64 || mediaType) {
    if (
      typeof imageBase64 !== "string" || !imageBase64 ||
      !VALID_MEDIA_TYPES.includes(mediaType as ImageMediaType)
    ) {
      return NextResponse.json(
        { success: false, error: "imageBase64 (string) and valid mediaType are required" },
        { status: 400 }
      );
    }
    const decodedBytes = Math.floor(imageBase64.length * 0.75);
    if (decodedBytes > MAX_BYTES) {
      return NextResponse.json(
        { success: false, error: "Image too large. Maximum size is ~3 MB." },
        { status: 413 }
      );
    }
    image = { base64: imageBase64, mediaType: mediaType as ImageMediaType };
  }

  // Must have at least one input
  if (!image && !caseId) {
    return NextResponse.json(
      { success: false, error: "Provide imageBase64 or a known caseId" },
      { status: 400 }
    );
  }

  try {
    // ── Step 1: acquire measurements ──────────────────────────────────────
    const pipelineData = await acquirePipelineData(image, caseId);

    // ── Step 2: choose prompt ─────────────────────────────────────────────
    const prompt = pipelineData ? pipelineData.claude_prompt : VISION_ONLY_PROMPT;

    // ── Step 3: call Claude (image always included when available) ────────
    const result = await callClaude(prompt, image);

    // ── Step 4: attach metadata ───────────────────────────────────────────
    if (pipelineData) {
      result.pipeline_classification = pipelineData.pipeline_classification ?? null;
      if (!result.caveats) {
        result.caveats =
          `Digitized via ${pipelineData.digitizer_method} at ${pipelineData.sampling_rate} Hz. ` +
          `Leads: ${pipelineData.leads_available.join(", ")}.`;
      }
    } else if (!result.caveats) {
      result.caveats = "Visual analysis only — no signal digitization was performed. Measurements are estimates.";
    }

    return NextResponse.json({ success: true, result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
