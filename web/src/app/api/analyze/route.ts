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

interface PipelineData {
  measurements: Record<string, unknown>;
  claude_prompt: string;
  digitizer_method: string;
  leads_available: string[];
  sampling_rate: number;
  pipeline_classification?: PipelineClassification | null;
}

interface PythonServiceResult extends PipelineData {
  success: true;
}

// ---------------------------------------------------------------------------
// Call the Python HTTP service to digitize + measure
// ---------------------------------------------------------------------------

async function runPythonPipeline(
  imageBase64: string,
  mediaType: string
): Promise<PythonServiceResult> {
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
    } catch { /* ignore parse errors */ }
    throw new Error(`Python pipeline failed: ${detail}`);
  }

  return res.json() as Promise<PythonServiceResult>;
}

// ---------------------------------------------------------------------------
// Direct Claude vision analysis — used when PYTHON_SERVICE_URL is not set
// ---------------------------------------------------------------------------

const DIRECT_CLAUDE_PROMPT = `You are an expert cardiologist performing a systematic ECG interpretation. Analyze this ECG image carefully and return ONLY a valid JSON object matching exactly this structure (no markdown, no extra text):

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

async function runDirectClaudeAnalysis(
  imageBase64: string,
  mediaType: AnalyzeRequest["mediaType"]
): Promise<EKGAnalysisResult> {
  const message = await anthropic.messages.create({
    model: process.env.CLAUDE_MODEL ?? "claude-haiku-4-5-20251001",
    max_tokens: 4096,
    messages: [
      {
        role: "user",
        content: [
          {
            type: "image",
            source: { type: "base64", media_type: mediaType, data: imageBase64 },
          },
          { type: "text", text: DIRECT_CLAUDE_PROMPT },
        ],
      },
    ],
  });

  const responseText =
    message.content[0].type === "text" ? message.content[0].text : "";

  const cleaned = responseText
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();

  const result = JSON.parse(cleaned) as EKGAnalysisResult;
  if (!result.caveats) {
    result.caveats = "Visual analysis only — no signal digitization was performed. Measurements are estimates.";
  }
  return result;
}

// ---------------------------------------------------------------------------
// Call Claude with measurements only for final interpretation (no image)
// ---------------------------------------------------------------------------

async function runClaudeInterpretation(
  claudePrompt: string
): Promise<EKGAnalysisResult> {
  const message = await anthropic.messages.create({
    model: process.env.CLAUDE_MODEL ?? "claude-haiku-4-5-20251001",
    max_tokens: 4096,
    messages: [
      {
        role: "user",
        content: [
          { type: "text", text: claudePrompt },
        ],
      },
    ],
  });

  const responseText =
    message.content[0].type === "text" ? message.content[0].text : "";

  const cleaned = responseText
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "")
    .trim();

  return JSON.parse(cleaned) as EKGAnalysisResult;
}

// ---------------------------------------------------------------------------
// Route handler
// ---------------------------------------------------------------------------

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

  // Reject oversized requests before parsing JSON (~4 MB base64 ≈ ~3 MB image)
  const contentLength = Number(req.headers.get("content-length") ?? 0);
  const MAX_BYTES = 4 * 1024 * 1024; // 4 MB
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

  const VALID_MEDIA_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"] as const;
  if (
    typeof imageBase64 !== "string" || !imageBase64 ||
    !VALID_MEDIA_TYPES.includes(mediaType as (typeof VALID_MEDIA_TYPES)[number])
  ) {
    return NextResponse.json(
      { success: false, error: "imageBase64 (string) and valid mediaType are required" },
      { status: 400 }
    );
  }

  // Guard against Content-Length bypass: check actual decoded size
  const decodedBytes = Math.floor(imageBase64.length * 0.75);
  if (decodedBytes > MAX_BYTES) {
    return NextResponse.json(
      { success: false, error: "Image too large. Maximum size is ~3 MB." },
      { status: 413 }
    );
  }

  // ---------------------------------------------------------------------------
  // Use pre-computed measurements for known training cases (fast path)
  // ---------------------------------------------------------------------------
  const precomputed = caseId
    ? (measurementsData as Record<string, PipelineData>)[caseId]
    : undefined;

  if (precomputed) {
    try {
      console.log(`\n=== CLAUDE PROMPT for caseId=${caseId} ===\n${precomputed.claude_prompt}\n=== END PROMPT ===\n`);
      const result = await runClaudeInterpretation(precomputed.claude_prompt);
      if (!result.caveats) {
        result.caveats =
          `Pre-computed via ${precomputed.digitizer_method} at ${precomputed.sampling_rate} Hz. ` +
          `Leads: ${precomputed.leads_available.join(", ")}.`;
      }
      result.pipeline_classification = precomputed.pipeline_classification ?? null;
      return NextResponse.json({ success: true, result });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
  }

  // ---------------------------------------------------------------------------
  // Full pipeline — call Python HTTP service for user-uploaded images,
  // or fall back to direct Claude vision analysis if service is not configured.
  // ---------------------------------------------------------------------------
  if (!process.env.PYTHON_SERVICE_URL) {
    try {
      const result = await runDirectClaudeAnalysis(imageBase64, mediaType);
      return NextResponse.json({ success: true, result });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
  }

  try {
    const pythonResult = await runPythonPipeline(imageBase64, mediaType);

    const result = await runClaudeInterpretation(pythonResult.claude_prompt);

    if (!result.caveats) {
      result.caveats =
        `Digitized via ${pythonResult.digitizer_method} at ${pythonResult.sampling_rate} Hz. ` +
        `Leads: ${pythonResult.leads_available.join(", ")}.`;
    }

    result.pipeline_classification = pythonResult.pipeline_classification ?? null;

    return NextResponse.json({ success: true, result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
