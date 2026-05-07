import { NextRequest, NextResponse } from "next/server";
import { checkRateLimit } from "@/lib/rateLimit";
import type {
  AnalyzeRequest,
  AnalyzeResponse,
  AnalyzeErrorResponse,
  EKGAnalysisResult,
  PipelineClassification,
} from "@/types/analysis";
import type {
  ImageMediaType,
  Image,
  PipelineData,
  PythonServiceResult,
  SignalMeasurements,
  RhythmRegularity,
  NormalizedSignal,
} from "@/types/pipeline";
import measurementsData from "@/data/measurements.json";
import { getDisplayName } from "@/lib/arrhythmia";

const PYTHON_SERVICE_URL = process.env.PYTHON_SERVICE_URL ?? "http://localhost:8000";
const PYTHON_API_KEY = process.env.PYTHON_API_KEY ?? "";

// ---------------------------------------------------------------------------
// Primitive coercions
// ---------------------------------------------------------------------------

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
  if (v === "regular" || v === "regularly_irregular" || v === "irregularly_irregular") return v;
  return "regular";
}

function confidenceBase(pc: PipelineClassification | null | undefined): number {
  if (!pc || pc.error) return 0.62;
  return Math.max(0.45, Math.min(0.96, pc.confidence));
}

// ---------------------------------------------------------------------------
// Signal normalization — computed once, passed to all downstream functions
// ---------------------------------------------------------------------------

function normalizeSignal(
  m: SignalMeasurements,
  pc: PipelineClassification | null,
): NormalizedSignal {
  const rrAll = Array.isArray(m.rr_intervals_ms)
    ? m.rr_intervals_ms.filter((v): v is number => typeof v === "number" && Number.isFinite(v))
    : [];
  const rr = rrAll.slice(0, 8);
  const hr = Math.round(toNumber(m.heart_rate_bpm, rr.length > 0 ? 60000 / (rr.reduce((a, b) => a + b, 0) / rr.length) : 0));
  const category = hr < 60 ? "bradycardia" : hr > 100 ? "tachycardia" : "normal";
  const regularity = toRegularity(m.regularity);
  const prMs = toNullableNumber(m.pr_interval_ms);
  const qrsMs = toNullableNumber(m.qrs_duration_ms);
  const qtcMs = toNullableNumber(m.qtc_ms);
  const qtMs = toNullableNumber(m.qt_ms);
  const qtcProlonged = typeof m.qtc_prolonged === "boolean" ? m.qtc_prolonged : (qtcMs !== null ? qtcMs >= 460 : null);
  const qrsWide = toBool(m.qrs_wide, qrsMs !== null ? qrsMs >= 120 : false);
  const pPresent = toBool(m.p_waves_present, true);
  const baseConf = confidenceBase(pc);
  const rhythmCode = pc?.primary_rhythm ?? "NSR";
  const rhythmDisplay = pc?.display_name ?? getDisplayName(rhythmCode);

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

  const ppIntervals = Array.isArray(m.pp_intervals_ms)
    ? (m.pp_intervals_ms as number[]).filter((v) => typeof v === "number" && v > 0)
    : [];
  const rrIntervals = rrAll.filter((v) => v > 0);

  return {
    hr, category, regularity, prMs, qrsMs, qtcMs, qtMs, qtcProlonged,
    qrsWide, pPresent, baseConf, rhythmCode, rhythmDisplay,
    elevatedLeads, depressedLeads, stDetails,
    rr, ppIntervals, rrIntervals,
    rhythmLead: m.rhythm_lead ?? "II",
  };
}

// ---------------------------------------------------------------------------
// Differentials — data-driven tables; add a new rhythm = one line
// ---------------------------------------------------------------------------

type DiffPair = [string, string];

/** Base differentials by rhythm code. */
const RHYTHM_DIFFERENTIALS: Partial<Record<string, DiffPair>> = {
  AF:   ["Atrial flutter with variable block", "Multifocal atrial tachycardia"],
  AFL:  ["Atrial fibrillation", "SVT"],
  SVT:  ["Atrial flutter with 2:1 block", "Sinus tachycardia"],
  VT:   ["SVT with aberrancy", "Accelerated idioventricular rhythm"],
  VF:   ["Artifact", "Polymorphic VT"],
  ASYS: ["Fine VF", "Lead disconnection/artifact"],
};

/** NSR sub-conditions checked in order when no modifier fires. */
const NSR_DIFFERENTIALS: Array<{ test: (s: NormalizedSignal) => boolean; result: DiffPair }> = [
  { test: s => s.hr > 100,                  result: ["Sinus tachycardia", "Atrial tachycardia"] },
  { test: s => s.hr < 60,                   result: ["Sinus bradycardia", "Junctional rhythm"] },
  { test: s => s.regularity !== "regular",  result: ["Atrial fibrillation", "Frequent ectopy"] },
];

/**
 * Priority modifiers evaluated before rhythm-specific tables.
 * First match wins (mirrors the original if/else-if chain).
 */
const DIFFERENTIAL_MODIFIERS: Array<{ test: (s: NormalizedSignal) => boolean; result: DiffPair }> = [
  { test: s => s.elevatedLeads.length > 0,
    result: ["Early repolarization variant", "Pericarditis / myocarditis"] },
  { test: s => s.depressedLeads.some(l => ["V1", "V2", "V3"].includes(l)),
    result: ["Posterior STEMI (reciprocal)", "Anterior Ischemia"] },
  { test: s => s.depressedLeads.length > 0,
    result: ["NSTEMI / unstable angina", "Rate-related ST depression"] },
  { test: s => s.qrsWide && ["NSR", "SB", "ST"].includes(s.rhythmCode),
    result: ["LBBB or RBBB", "Aberrant conduction / Wolff-Parkinson-White"] },
  { test: s => s.hr < 50 && ["SB", "NSR"].includes(s.rhythmCode) && !s.qrsWide,
    result: ["High-degree AV block (2nd or 3rd degree)", "Junctional bradycardia"] },
  { test: s => s.hr < 50 && ["SB", "NSR"].includes(s.rhythmCode) && s.qrsWide,
    result: ["Complete (3rd degree) AV block with ventricular escape", "Accelerated idioventricular rhythm"] },
];

function inferDifferentials(s: NormalizedSignal): string[] {
  for (const mod of DIFFERENTIAL_MODIFIERS) {
    if (mod.test(s)) return mod.result;
  }
  const rhythmPair = RHYTHM_DIFFERENTIALS[s.rhythmCode];
  if (rhythmPair) return rhythmPair;
  for (const nsr of NSR_DIFFERENTIALS) {
    if (nsr.test(s)) return nsr.result;
  }
  return [];
}

// ---------------------------------------------------------------------------
// Morphological findings — rule table; add a new finding = one entry
// ---------------------------------------------------------------------------

interface MorphologicalRule {
  test: (s: NormalizedSignal) => boolean;
  finding: (s: NormalizedSignal) => string;
}

const MORPHOLOGICAL_RULES: MorphologicalRule[] = [
  {
    test: s => s.qrsWide,
    finding: () => "Wide QRS (≥120 ms) — consider LBBB, RBBB, or aberrant conduction",
  },
  {
    test: s => s.prMs !== null && s.prMs > 200,
    finding: s => `Prolonged PR (${Math.round(s.prMs!)} ms) — consider 1st degree AV block`,
  },
  {
    test: s => !s.pPresent && s.rhythmCode === "NSR",
    finding: () => "P waves not detected — consider junctional rhythm or accelerated idioventricular rhythm",
  },
  {
    test: s => s.qtcMs !== null && s.qtcMs >= 500,
    finding: s => `Markedly prolonged QTc (${Math.round(s.qtcMs!)} ms) — consider Long QT syndrome, drug effect`,
  },
  {
    test: s => s.qtcMs !== null && s.qtcMs >= 460 && s.qtcMs < 500,
    finding: s => `Prolonged QTc (${Math.round(s.qtcMs!)} ms)`,
  },
];

/**
 * AV block detection from PP/RR rate comparison.
 * Kept as a dedicated function because it requires intermediate rate calculations,
 * not just a boolean predicate on NormalizedSignal.
 */
function avBlockFinding(s: NormalizedSignal): string | null {
  const { ppIntervals, rrIntervals, hr, pPresent, rhythmCode, qrsWide } = s;

  if (ppIntervals.length >= 2 && rrIntervals.length >= 2) {
    const meanPP = ppIntervals.reduce((a, b) => a + b, 0) / ppIntervals.length;
    const meanRR = rrIntervals.reduce((a, b) => a + b, 0) / rrIntervals.length;
    const atrialRate = Math.round(60000 / meanPP);
    const ventricularRate = Math.round(60000 / meanRR);
    const ppCV = Math.sqrt(
      ppIntervals.reduce((sum, v) => sum + (v - meanPP) ** 2, 0) / ppIntervals.length
    ) / meanPP;

    if (atrialRate > ventricularRate * 1.3 && ventricularRate < 65 && ppCV < 0.15) {
      const escapeType = qrsWide ? "ventricular escape" : "junctional escape";
      return (
        `Atrial rate ${atrialRate} bpm vs ventricular rate ${ventricularRate} bpm — ` +
        `P-QRS dissociation pattern; consider complete (3rd degree) AV block with ${escapeType}`
      );
    }
    if (ventricularRate < 55 && pPresent && ["SB", "NSR"].includes(rhythmCode) && atrialRate > ventricularRate) {
      return `Bradycardia (ventricular ${ventricularRate} bpm, atrial ~${atrialRate} bpm) — consider high-degree AV block`;
    }
  } else if (hr < 50 && pPresent && ["SB", "NSR"].includes(rhythmCode)) {
    return "Marked bradycardia with P waves present — consider high-degree AV block";
  }
  return null;
}

function morphologicalFindings(s: NormalizedSignal): string[] {
  const findings: string[] = [];
  for (const rule of MORPHOLOGICAL_RULES) {
    if (rule.test(s)) findings.push(rule.finding(s));
  }
  const avBlock = avBlockFinding(s);
  if (avBlock) findings.push(avBlock);
  return findings;
}

// ---------------------------------------------------------------------------
// Clinical impression
// ---------------------------------------------------------------------------

function deriveClinicalImpression(s: NormalizedSignal, extraFindings: string[]): string {
  const parts: string[] =
    s.elevatedLeads.length > 0
      ? [`STEMI — ${s.rhythmDisplay} (elevation in ${s.elevatedLeads.join(", ")})`]
      : s.depressedLeads.length > 0
        ? [`Ischemia / NSTEMI — ${s.rhythmDisplay} (depression in ${s.depressedLeads.join(", ")})`]
        : [s.rhythmDisplay];
  parts.push(...extraFindings);
  return parts.join("; ");
}

// ---------------------------------------------------------------------------
// Ten-step explanation
// ---------------------------------------------------------------------------

function buildTenStepExplanation(
  s: NormalizedSignal,
  pc: PipelineClassification | null,
  clinicalImpression: string,
): string {
  const step6 = s.qrsWide
    ? `Wide-complex pattern (${s.qrsMs !== null ? `${Math.round(s.qrsMs)} ms` : "≥120 ms"}) — consider LBBB, RBBB, or aberrant conduction. Morphology differentiation requires 12-lead.`
    : "Narrow QRS — no bundle branch block pattern detected.";

  const step7 =
    s.elevatedLeads.length > 0
      ? `ST elevation noted in ${s.elevatedLeads.join(", ")} — consider STEMI until proven otherwise.`
      : s.depressedLeads.length > 0
        ? `ST depression noted in ${s.depressedLeads.join(", ")} — consider ischemia / NSTEMI.`
        : "No significant ST shift detected.";

  const mode = pc?.used_deep_learning ? "deep-learning-assisted" : "signal-rule-based";
  return [
    `1) Rate: approximately ${s.hr} bpm from detected R-R intervals.`,
    `2) Rhythm: ${s.regularity.replace(/_/g, " ")}.`,
    `3) P waves: ${s.pPresent ? "present" : "not clearly present"}.`,
    `4) PR interval: ${s.prMs !== null ? `${Math.round(s.prMs)} ms${s.prMs > 200 ? " — prolonged, consider 1st degree AV block" : ""}` : "not reliably measurable"}.`,
    `5) QRS duration: ${s.qrsMs !== null ? `${Math.round(s.qrsMs)} ms` : "not reliably measurable"}${s.qrsWide ? " (wide)" : " (narrow)"}.`,
    `6) QRS morphology: ${step6}`,
    `7) ST segment: ${step7}`,
    "8) T waves: no definitive morphology classification from this signal-only pass.",
    `9) QTc: ${s.qtcMs !== null ? `${Math.round(s.qtcMs)} ms${s.qtcMs >= 460 ? " — prolonged" : ""}` : "not reliably measurable"}.`,
    `10) Impression: ${clinicalImpression} (${mode} pipeline).`,
  ].join(" ");
}

// ---------------------------------------------------------------------------
// Result assembly
// ---------------------------------------------------------------------------

function toTenStepResult(data: PipelineData): EKGAnalysisResult {
  const m = (data.measurements ?? {}) as SignalMeasurements;
  const pc = data.pipeline_classification && !data.pipeline_classification.error
    ? data.pipeline_classification
    : null;

  const s = normalizeSignal(m, pc);
  const extraFindings = morphologicalFindings(s);
  const clinicalImpression = deriveClinicalImpression(s, extraFindings);
  const imageQuality = data.digitizer_method.includes("uncalibrated") ? "fair" : "good";
  const caveatBits = [
    `Digitized via ${data.digitizer_method} at ${data.sampling_rate} Hz`,
    `Lead used for rhythm: ${s.rhythmLead}`,
    ...(!pc?.used_deep_learning ? ["Deep model unavailable - used signal-rule classifier"] : []),
  ];

  return {
    rate: {
      bpm: s.hr,
      rr_intervals_ms: s.rr.map((v) => Math.round(v)),
      category: s.category,
      method: "PhysioNet signal pipeline",
      confidence: Math.min(0.95, s.baseConf),
    },
    rhythm: {
      regularity: s.regularity,
      confidence: Math.min(0.95, s.baseConf),
    },
    p_waves: {
      present: s.pPresent,
      morphology: s.pPresent ? "Detected on rhythm lead" : "Not clearly detected",
      ratio: s.pPresent ? "1:1 (inferred)" : null,
      confidence: Math.max(0.55, s.baseConf - 0.08),
    },
    pr_interval: {
      ms: s.prMs !== null ? Math.round(s.prMs) : null,
      measured_beats: s.prMs !== null ? [Math.round(s.prMs)] : [],
      normal: s.prMs !== null ? s.prMs >= 120 && s.prMs <= 200 : null,
      fixed: s.regularity === "regular" ? true : null,
      confidence: Math.max(0.5, s.baseConf - 0.1),
    },
    qrs: {
      duration_ms: s.qrsMs !== null ? Math.round(s.qrsMs) : null,
      measured_beats_ms: s.qrsMs !== null ? [Math.round(s.qrsMs)] : [],
      wide: s.qrsWide,
      morphology: s.qrsWide
        ? "Wide-complex — consider LBBB, RBBB, or aberrant conduction"
        : "Narrow — no bundle branch block pattern detected",
      confidence: Math.max(0.55, s.baseConf - 0.06),
    },
    st_segment: {
      elevation: s.elevatedLeads.length > 0,
      depression: s.depressedLeads.length > 0,
      details: s.stDetails,
      confidence: Math.max(0.5, s.baseConf - 0.12),
    },
    t_waves: {
      morphology: "Not robustly classified by current signal pipeline",
      confidence: 0.4,
    },
    qtc: {
      ms: s.qtcMs !== null ? Math.round(s.qtcMs) : null,
      measured_qt_ms: s.qtMs !== null ? [Math.round(s.qtMs)] : [],
      prolonged: s.qtcProlonged,
      confidence: Math.max(0.5, s.baseConf - 0.12),
    },
    primary_rhythm: s.rhythmDisplay,
    clinical_impression: clinicalImpression,
    overall_confidence: Math.min(0.96, Math.max(0.45, s.baseConf)),
    differentials: inferDifferentials(s),
    explanation: buildTenStepExplanation(s, pc, clinicalImpression),
    image_quality: imageQuality,
    caveats: `${caveatBits.join(". ")}.`,
    pipeline_classification: data.pipeline_classification ?? null,
  };
}

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
    const result = toTenStepResult(pipelineData);
    return NextResponse.json({ success: true, result });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ success: false, error: message }, { status: 500 });
  }
}
