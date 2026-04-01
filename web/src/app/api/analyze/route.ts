import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";
import { checkRateLimit } from "@/lib/rateLimit";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  AnalyzeErrorResponse,
  EKGAnalysisResult,
} from "@/types/analysis";
import { spawn } from "child_process";
import { writeFile, unlink } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { randomUUID } from "crypto";
import measurementsData from "@/data/measurements.json";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

// Path to the Python script, relative to project root
const PYTHON_SCRIPT = join(process.cwd(), "..", "python", "analyze_ecg.py");
const PYTHON_BIN = process.env.PYTHON_BIN ?? "python3";

// ---------------------------------------------------------------------------
// Run the Python digitizer + BioSPPy pipeline
// ---------------------------------------------------------------------------

interface PipelineData {
  measurements: Record<string, unknown>;
  claude_prompt: string;
  digitizer_method: string;
  leads_available: string[];
  sampling_rate: number;
}

interface PythonResult extends PipelineData {
  success: true;
}

interface PythonError {
  success: false;
  error: string;
  traceback?: string;
}

async function runPythonPipeline(imagePath: string): Promise<PythonResult> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    const errChunks: Buffer[] = [];

    const proc = spawn(PYTHON_BIN, [PYTHON_SCRIPT, "--image", imagePath]);

    proc.stdout.on("data", (chunk: Buffer) => chunks.push(chunk));
    proc.stderr.on("data", (chunk: Buffer) => errChunks.push(chunk));

    proc.on("close", (code) => {
      const stdout = Buffer.concat(chunks).toString("utf8").trim();
      const stderr = Buffer.concat(errChunks).toString("utf8").trim();

      if (code !== 0) {
        let errMsg = `Python pipeline exited with code ${code}`;
        try {
          const parsed: PythonError = JSON.parse(stderr);
          errMsg = parsed.error ?? errMsg;
        } catch {
          if (stderr) errMsg += `: ${stderr}`;
        }
        return reject(new Error(errMsg));
      }

      try {
        const result = JSON.parse(stdout) as PythonResult | PythonError;
        if (!result.success) {
          return reject(new Error((result as PythonError).error));
        }
        resolve(result as PythonResult);
      } catch {
        reject(new Error(`Python pipeline returned unparseable output: ${stdout.slice(0, 200)}`));
      }
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to start Python process: ${err.message}`));
    });
  });
}

// ---------------------------------------------------------------------------
// Call Claude with measurements + image for final interpretation
// ---------------------------------------------------------------------------

async function runClaudeInterpretation(
  imageBase64: string,
  mediaType: AnalyzeRequest["mediaType"],
  claudePrompt: string
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
      const result = await runClaudeInterpretation(
        imageBase64,
        mediaType,
        precomputed.claude_prompt
      );
      if (!result.caveats) {
        result.caveats =
          `Pre-computed via ${precomputed.digitizer_method} at ${precomputed.sampling_rate} Hz. ` +
          `Leads: ${precomputed.leads_available.join(", ")}.`;
      }
      return NextResponse.json({ success: true, result });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      return NextResponse.json({ success: false, error: message }, { status: 500 });
    }
  }

  // ---------------------------------------------------------------------------
  // Full pipeline for user-uploaded images
  // ---------------------------------------------------------------------------
  const ext = mediaType.split("/")[1].replace("jpeg", "jpg");
  const tmpPath = join(tmpdir(), `ecg-${randomUUID()}.${ext}`);

  try {
    await writeFile(tmpPath, Buffer.from(imageBase64, "base64"));

    // Step 1: digitize + measure
    const pythonResult = await runPythonPipeline(tmpPath);

    // Step 2: Claude interprets measurements + image
    const result = await runClaudeInterpretation(
      imageBase64,
      mediaType,
      pythonResult.claude_prompt
    );

    if (!result.caveats) {
      result.caveats =
        `Digitized via ${pythonResult.digitizer_method} at ${pythonResult.sampling_rate} Hz. ` +
        `Leads: ${pythonResult.leads_available.join(", ")}.`;
    }

    return NextResponse.json({ success: true, result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  } finally {
    await unlink(tmpPath).catch(() => {});
  }
}
