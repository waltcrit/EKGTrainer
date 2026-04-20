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
import { getDisplayName } from "@/lib/arrhythmia";

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

type RhythmRegularity = "regular" | "regularly_irregular" | "irregularly_irregular";

interface SignalMeasurements {
  r_peaks?: number[];
  rr_intervals_ms?: number[];
  heart_rate_bpm?: number;
  regularity?: RhythmRegularity | string;
  p_waves_present?: boolean;
  pr_interval_ms?: number | null;
  qrs_duration_ms?: number | null;
  qrs_wide?: boolean;
  qt_ms?: number | null;
  qtc_ms?: number | null;
  qtc_prolonged?: boolean | null;
  st?: Record<string, { elevation?: boolean; depression?: boolean; mean_mv?: number }>;
  num_beats?: number;
  rhythm_lead?: string;
  p_peaks?: number[];
  pp_intervals_ms?: number[];
}

function toNumber(v: unknown, fallback = 0): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

function toNullableNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function toBool(v: unknown, fallback = false): boolean {
  return typeof v === "boolean" ? v : fallback;
}

function toRegularity(v: unknown): RhythmRegularity {
  if (v === "regular" || v === "regularly_irregular" || v === "irregularly_irregular") {
    return v;
  }
  return "regular";
}

function confidenceBase(pc: PipelineClassification | null | undefined): number {
  if (!pc || pc.error) return 0.62;
  return Math.max(0.45, Math.min(0.96, pc.confidence));
}

function inferDifferentials(
  primaryCode: string,
  hr: number,
  regularity: RhythmRegularity,
  elevated: string[],
  depressed: string[],
  qrsWide: boolean,
): string[] {
  const d: string[] = [];

  if (elevated.length > 0) {
    d.push("Early repolarization variant", "Pericarditis / myocarditis");
  } else if (depressed.length > 0) {
    d.push("NSTEMI / unstable angina", "Rate-related ST depression");
  } else if (qrsWide && (primaryCode === "NSR" || primaryCode === "SB" || primaryCode === "ST")) {
    // Wide QRS with sinus rhythm — the rhythm classifier missed the conduction abnormality
    d.push("LBBB or RBBB", "Aberrant conduction / Wolff-Parkinson-White");
  } else if (hr < 50 && (primaryCode === "SB" || primaryCode === "NSR") && !qrsWide) {
    d.push("High-degree AV block (2nd or 3rd degree)", "Junctional bradycardia");
  } else if (hr < 50 && (primaryCode === "SB" || primaryCode === "NSR") && qrsWide) {
    d.push("Complete (3rd degree) AV block with ventricular escape", "Accelerated idioventricular rhythm");
  } else {
    if (primaryCode === "AF") d.push("Atrial flutter with variable block", "Multifocal atrial tachycardia");
    if (primaryCode === "AFL") d.push("Atrial fibrillation", "SVT");
    if (primaryCode === "SVT") d.push("Atrial flutter with 2:1 block", "Sinus tachycardia");
    if (primaryCode === "VT") d.push("SVT with aberrancy", "Accelerated idioventricular rhythm");
    if (primaryCode === "VF") d.push("Artifact", "Polymorphic VT");
    if (primaryCode === "ASYS") d.push("Fine VF", "Lead disconnection/artifact");
    if (primaryCode === "NSR" && hr > 100) d.push("Sinus tachycardia", "Atrial tachycardia");
    if (primaryCode === "NSR" && hr < 60) d.push("Sinus bradycardia", "Junctional rhythm");
    if (primaryCode === "NSR" && regularity !== "regular") d.push("Atrial fibrillation", "Frequent ectopy");
  }
  return d.slice(0, 2);
}

/**
 * Build a list of morphological findings from signal measurements.
 * These are findings that the rhythm classifier cannot express (e.g. LBBB, AV block).
 */
function morphologicalFindings(m: SignalMeasurements, rhythmCode: string): string[] {
  const findings: string[] = [];
  const hr = Math.round(toNumber(m.heart_rate_bpm));
  const pr = toNullableNumber(m.pr_interval_ms);
  const qrs = toNullableNumber(m.qrs_duration_ms);
  const qtcMs = toNullableNumber(m.qtc_ms);
  const qrsWide = toBool(m.qrs_wide, qrs !== null ? qrs >= 120 : false);
  const pPresent = toBool(m.p_waves_present, true);

  // Wide QRS — can't distinguish LBBB/RBBB/aberrancy without 12-lead morphology
  if (qrsWide) {
    findings.push("Wide QRS (≥120 ms) — consider LBBB, RBBB, or aberrant conduction");
  }

  // 1st degree AV block
  if (pr !== null && pr > 200) {
    findings.push(`Prolonged PR (${Math.round(pr)} ms) — consider 1st degree AV block`);
  }

  // AV block detection using P-P vs R-R rate comparison
  const ppIntervals = Array.isArray(m.pp_intervals_ms)
    ? (m.pp_intervals_ms as number[]).filter((v) => typeof v === "number" && v > 0)
    : [];
  const rrIntervals = Array.isArray(m.rr_intervals_ms)
    ? (m.rr_intervals_ms as number[]).filter((v) => typeof v === "number" && v > 0)
    : [];

  if (ppIntervals.length >= 2 && rrIntervals.length >= 2) {
    const meanPP = ppIntervals.reduce((a, b) => a + b, 0) / ppIntervals.length;
    const meanRR = rrIntervals.reduce((a, b) => a + b, 0) / rrIntervals.length;
    const atrialRate = Math.round(60000 / meanPP);
    const ventricularRate = Math.round(60000 / meanRR);

    // P-P regularity: CV of PP intervals
    const ppCV = Math.sqrt(
      ppIntervals.reduce((sum, v) => sum + (v - meanPP) ** 2, 0) / ppIntervals.length
    ) / meanPP;

    if (
      atrialRate > ventricularRate * 1.3 &&
      ventricularRate < 65 &&
      ppCV < 0.15  // P-P is regular (not AF/MAT)
    ) {
      // Atrial rate materially faster than ventricular with regular P-P → AV dissociation
      const escapeType = qrsWide ? "ventricular escape" : "junctional escape";
      findings.push(
        `Atrial rate ${atrialRate} bpm vs ventricular rate ${ventricularRate} bpm — ` +
        `P-QRS dissociation pattern; consider complete (3rd degree) AV block with ${escapeType}`
      );
    } else if (
      ventricularRate < 55 &&
      pPresent &&
      (rhythmCode === "SB" || rhythmCode === "NSR") &&
      atrialRate > ventricularRate
    ) {
      // Softer signal: slower-than-expected rate with P waves and some PP/RR discordance
      findings.push(`Bradycardia (ventricular ${ventricularRate} bpm, atrial ~${atrialRate} bpm) — consider high-degree AV block`);
    }
  } else if (hr < 50 && pPresent && (rhythmCode === "SB" || rhythmCode === "NSR")) {
    // Fallback when PP data unavailable
    findings.push("Marked bradycardia with P waves present — consider high-degree AV block");
  }

  // Absent P waves not already captured by AF/AFL/VT etc.
  if (!pPresent && rhythmCode === "NSR") {
    findings.push("P waves not detected — consider junctional rhythm or accelerated idioventricular rhythm");
  }

  // QTc prolongation
  if (qtcMs !== null && qtcMs >= 500) {
    findings.push(`Markedly prolonged QTc (${Math.round(qtcMs)} ms) — consider Long QT syndrome, drug effect`);
  } else if (qtcMs !== null && qtcMs >= 460) {
    findings.push(`Prolonged QTc (${Math.round(qtcMs)} ms)`);
  }

  return findings;
}

/** Derive clinical impression from rhythm + ST findings + morphological flags. */
function deriveClinicalImpression(
  rhythmDisplay: string,
  elevated: string[],
  depressed: string[],
  extraFindings: string[],
): string {
  const parts: string[] = [];

  if (elevated.length > 0) {
    parts.push(`STEMI — ${rhythmDisplay} (elevation in ${elevated.join(", ")})`);
  } else if (depressed.length > 0) {
    parts.push(`Ischemia / NSTEMI — ${rhythmDisplay} (depression in ${depressed.join(", ")})`);
  } else {
    parts.push(rhythmDisplay);
  }

  parts.push(...extraFindings);
  return parts.join("; ");
}

function buildTenStepExplanation(
  m: SignalMeasurements,
  pc: PipelineClassification | null,
  clinicalImpression: string,
  regularity: RhythmRegularity,
): string {
  const hr = Math.round(toNumber(m.heart_rate_bpm));
  const pr = toNullableNumber(m.pr_interval_ms);
  const qrs = toNullableNumber(m.qrs_duration_ms);
  const qtc = toNullableNumber(m.qtc_ms);
  const pPresent = toBool(m.p_waves_present, true);
  const qrsWide = toBool(m.qrs_wide, qrs !== null ? qrs >= 120 : false);
  const st = m.st ?? {};
  const elevated = Object.entries(st).filter(([, s]) => s?.elevation).map(([lead]) => lead);
  const depressed = Object.entries(st).filter(([, s]) => s?.depression).map(([lead]) => lead);

  const step6 = qrsWide
    ? `Wide-complex pattern (${qrs !== null ? `${Math.round(qrs)} ms` : "≥120 ms"}) — consider LBBB, RBBB, or aberrant conduction. Morphology differentiation requires 12-lead.`
    : "Narrow QRS — no bundle branch block pattern detected.";

  const step7 =
    elevated.length > 0
      ? `ST elevation noted in ${elevated.join(", ")} — consider STEMI until proven otherwise.`
      : depressed.length > 0
        ? `ST depression noted in ${depressed.join(", ")} — consider ischemia / NSTEMI.`
        : "No significant ST shift detected.";

  const mode = pc?.used_deep_learning ? "deep-learning-assisted" : "signal-rule-based";
  return [
    `1) Rate: approximately ${hr} bpm from detected R-R intervals.`,
    `2) Rhythm: ${regularity.replace(/_/g, " ")}.`,
    `3) P waves: ${pPresent ? "present" : "not clearly present"}.`,
    `4) PR interval: ${pr !== null ? `${Math.round(pr)} ms${pr > 200 ? " — prolonged, consider 1st degree AV block" : ""}` : "not reliably measurable"}.`,
    `5) QRS duration: ${qrs !== null ? `${Math.round(qrs)} ms` : "not reliably measurable"}${qrsWide ? " (wide)" : " (narrow)"}.`,
    `6) QRS morphology: ${step6}`,
    `7) ST segment: ${step7}`,
    "8) T waves: no definitive morphology classification from this signal-only pass.",
    `9) QTc: ${qtc !== null ? `${Math.round(qtc)} ms${qtc >= 460 ? " — prolonged" : ""}` : "not reliably measurable"}.`,
    `10) Impression: ${clinicalImpression} (${mode} pipeline).`,
  ].join(" ");
}

function toTenStepResult(data: PipelineData): EKGAnalysisResult {
  const m = (data.measurements ?? {}) as SignalMeasurements;
  const pc = data.pipeline_classification && !data.pipeline_classification.error
    ? data.pipeline_classification
    : null;

  const rhythmCode = pc?.primary_rhythm ?? "NSR";
  const rhythmDisplay = pc?.display_name ?? getDisplayName(rhythmCode);

  const rr = Array.isArray(m.rr_intervals_ms)
    ? m.rr_intervals_ms.filter((v): v is number => typeof v === "number" && Number.isFinite(v)).slice(0, 8)
    : [];

  const bpm = Math.round(toNumber(m.heart_rate_bpm, rr.length > 0 ? 60000 / (rr.reduce((a, b) => a + b, 0) / rr.length) : 0));
  const category = bpm < 60 ? "bradycardia" : bpm > 100 ? "tachycardia" : "normal";
  const regularity = toRegularity(m.regularity);
  const prMs = toNullableNumber(m.pr_interval_ms);
  const qrsMs = toNullableNumber(m.qrs_duration_ms);
  const qtcMs = toNullableNumber(m.qtc_ms);
  const qtMs = toNullableNumber(m.qt_ms);
  const qtcProlonged = typeof m.qtc_prolonged === "boolean" ? m.qtc_prolonged : (qtcMs !== null ? qtcMs >= 460 : null);
  const baseConf = confidenceBase(pc);

  const st = m.st ?? {};
  const elevatedEntries = Object.entries(st).filter(([, s]) => s?.elevation);
  const depressedEntries = Object.entries(st).filter(([, s]) => s?.depression);
  const elevatedLeads = elevatedEntries.map(([lead]) => lead);
  const depressedLeads = depressedEntries.map(([lead]) => lead);
  const stDetails =
    elevatedEntries.length > 0
      ? `Elevation in ${elevatedEntries.map(([lead, v]) => `${lead}${typeof v?.mean_mv === "number" ? ` (${v.mean_mv.toFixed(2)} mV)` : ""}`).join(", ")}`
      : depressedEntries.length > 0
        ? `Depression in ${depressedEntries.map(([lead, v]) => `${lead}${typeof v?.mean_mv === "number" ? ` (${v.mean_mv.toFixed(2)} mV)` : ""}`).join(", ")}`
        : null;

  const extraFindings = morphologicalFindings(m, rhythmCode);
  const clinicalImpression = deriveClinicalImpression(rhythmDisplay, elevatedLeads, depressedLeads, extraFindings);

  const imageQuality = data.digitizer_method.includes("uncalibrated") ? "fair" : "good";
  const caveatBits: string[] = [
    `Digitized via ${data.digitizer_method} at ${data.sampling_rate} Hz`,
    `Lead used for rhythm: ${m.rhythm_lead ?? "II"}`,
  ];
  if (!pc?.used_deep_learning) caveatBits.push("Deep model unavailable - used signal-rule classifier");

  return {
    rate: {
      bpm,
      rr_intervals_ms: rr.map((v) => Math.round(v)),
      category,
      method: "PhysioNet signal pipeline",
      confidence: Math.min(0.95, baseConf),
    },
    rhythm: {
      regularity,
      confidence: Math.min(0.95, baseConf),
    },
    p_waves: {
      present: toBool(m.p_waves_present, true),
      morphology: toBool(m.p_waves_present, true) ? "Detected on rhythm lead" : "Not clearly detected",
      ratio: toBool(m.p_waves_present, true) ? "1:1 (inferred)" : null,
      confidence: Math.max(0.55, baseConf - 0.08),
    },
    pr_interval: {
      ms: prMs !== null ? Math.round(prMs) : null,
      measured_beats: prMs !== null ? [Math.round(prMs)] : [],
      normal: prMs !== null ? prMs >= 120 && prMs <= 200 : null,
      fixed: regularity === "regular" ? true : null,
      confidence: Math.max(0.5, baseConf - 0.1),
    },
    qrs: {
      duration_ms: qrsMs !== null ? Math.round(qrsMs) : null,
      measured_beats_ms: qrsMs !== null ? [Math.round(qrsMs)] : [],
      wide: toBool(m.qrs_wide, qrsMs !== null ? qrsMs >= 120 : false),
      morphology: toBool(m.qrs_wide, qrsMs !== null ? qrsMs >= 120 : false) ? "Wide-complex — consider LBBB, RBBB, or aberrant conduction" : "Narrow — no bundle branch block pattern detected",
      confidence: Math.max(0.55, baseConf - 0.06),
    },
    st_segment: {
      elevation: elevatedLeads.length > 0,
      depression: depressedLeads.length > 0,
      details: stDetails,
      confidence: Math.max(0.5, baseConf - 0.12),
    },
    t_waves: {
      morphology: "Not robustly classified by current signal pipeline",
      confidence: 0.4,
    },
    qtc: {
      ms: qtcMs !== null ? Math.round(qtcMs) : null,
      measured_qt_ms: qtMs !== null ? [Math.round(qtMs)] : [],
      prolonged: qtcProlonged,
      confidence: Math.max(0.5, baseConf - 0.12),
    },
    primary_rhythm: rhythmDisplay,
    clinical_impression: clinicalImpression,
    overall_confidence: Math.min(0.96, Math.max(0.45, baseConf)),
    differentials: inferDifferentials(rhythmCode, bpm, regularity, elevatedLeads, depressedLeads, toBool(m.qrs_wide, qrsMs !== null ? qrsMs >= 120 : false)),
    explanation: buildTenStepExplanation(m, pc, clinicalImpression, regularity),
    image_quality: imageQuality,
    caveats: `${caveatBits.join(". ")}.`,
    pipeline_classification: data.pipeline_classification ?? null,
  };
}

// ---------------------------------------------------------------------------
// Step 1 — Acquire pipeline data (measurements + Claude prompt)
//
// Strategies in priority order:
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
    if (precomputed) {
      return precomputed;
    }
  }

  if (image) {
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
const MAX_BYTES = 4 * 1024 * 1024; // 4 MB

export async function POST(
  req: NextRequest
): Promise<NextResponse<AnalyzeResponse | AnalyzeErrorResponse>> {
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
    // ── Step 1: acquire PhysioNet-compatible pipeline data ────────────────
    const pipelineData = await acquirePipelineData(image, caseId);

    if (!pipelineData) {
      return NextResponse.json(
        {
          success: false,
          error:
            "Signal pipeline data unavailable. Provide a known caseId or enable the Python PhysioNet service.",
        },
        { status: 503 }
      );
    }

    // ── Step 2: format direct 10-step output from signal pipeline ────────
    const result = toTenStepResult(pipelineData);

    return NextResponse.json({ success: true, result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
