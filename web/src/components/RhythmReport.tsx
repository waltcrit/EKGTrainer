"use client";

import type { EKGAnalysisResult, PipelineClassification } from "@/types/analysis";
import { getDisplayName, getStyle } from "@/lib/arrhythmia";

interface RhythmReportProps {
  result: EKGAnalysisResult;
}

const WIDTH_CLASSES = [
  "w-0",
  "w-[5%]",
  "w-[10%]",
  "w-[15%]",
  "w-[20%]",
  "w-[25%]",
  "w-[30%]",
  "w-[35%]",
  "w-[40%]",
  "w-[45%]",
  "w-[50%]",
  "w-[55%]",
  "w-[60%]",
  "w-[65%]",
  "w-[70%]",
  "w-[75%]",
  "w-[80%]",
  "w-[85%]",
  "w-[90%]",
  "w-[95%]",
  "w-full",
] as const;

function widthClassFromConfidence(value: number): (typeof WIDTH_CLASSES)[number] {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  const step = Math.round(pct / 5);
  return WIDTH_CLASSES[step] ?? "w-0";
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const fill =
    pct >= 80 ? "bg-emerald-500" :
    pct >= 60 ? "bg-amber-400"  : "bg-red-400";
  const widthClass = widthClassFromConfidence(value);
  return (
    <div className="flex items-center gap-2 shrink-0">
      <div className="w-14 h-1.5 bg-[var(--academy-line)] rounded-full overflow-hidden">
        <div className={`${widthClass} h-full rounded-full ${fill}`} />
      </div>
      <span className="text-[10px] text-[var(--academy-muted)] w-7 text-right">{pct}%</span>
    </div>
  );
}

function Row({ label, value, confidence }: {
  label: string;
  value: string | null;
  confidence?: number;
}) {
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-[var(--academy-line)] last:border-0">
      <span className="text-xs font-semibold text-[var(--academy-muted)] w-24 shrink-0">{label}</span>
      <span className="text-sm text-[var(--academy-ink)] flex-1 leading-snug">{value ?? "—"}</span>
      {confidence !== undefined && <ConfidenceBar value={confidence} />}
    </div>
  );
}

function PipelineClassificationBadge({ pc }: { pc: PipelineClassification }) {
  if (pc.error) return null;
  const style = getStyle(pc.primary_rhythm);
  const pct = Math.round(pc.confidence * 100);
  const widthClass = widthClassFromConfidence(pc.confidence);
  const barFill =
    pct >= 80 ? "bg-emerald-500" :
    pct >= 60 ? "bg-amber-400"  : "bg-red-400";

  return (
    <div className="rounded-xl border border-[var(--academy-line)] bg-[var(--academy-bg)] px-4 py-3 flex items-center gap-3">
      <div className="shrink-0">
        <svg className="w-3.5 h-3.5 text-[var(--academy-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-0.5">
          Signal Pipeline
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${style.textClass} ${style.bgClass}`}>
            {getDisplayName(pc.primary_rhythm)}
          </span>
          {pc.used_deep_learning && (
            <span className="text-[10px] text-[var(--academy-muted)]">deep model</span>
          )}
          {pc.notes.length > 0 && (
            <span className="text-[10px] text-[var(--academy-muted)] italic truncate">
              {pc.notes[0]}
            </span>
          )}
        </div>
      </div>
      <div className="shrink-0 flex items-center gap-1.5">
        <div className="w-10 h-1.5 bg-[var(--academy-line)] rounded-full overflow-hidden">
          <div className={`${widthClass} h-full rounded-full ${barFill}`} />
        </div>
        <span className="text-[10px] text-[var(--academy-muted)] w-6 text-right">{pct}%</span>
      </div>
    </div>
  );
}

const IMAGE_QUALITY_COLOR: Record<string, string> = {
  good: "text-emerald-600",
  fair: "text-amber-600",
  poor: "text-red-600",
};

export default function RhythmReport({ result }: RhythmReportProps) {
  const overallPct = Math.round(result.overall_confidence * 100);
  const ringColor  =
    overallPct >= 80 ? "text-emerald-600" :
    overallPct >= 60 ? "text-amber-500"   : "text-red-500";
  const ringBg =
    overallPct >= 80 ? "bg-emerald-50 border-emerald-200" :
    overallPct >= 60 ? "bg-amber-50 border-amber-200"     : "bg-red-50 border-red-200";

  return (
    <div className="flex flex-col gap-3">

      {/* ── Analysis mode ─────────────────────────────────────────────── */}
      <div className="academy-panel rounded-xl border border-teal-200 bg-teal-50/80 px-4 py-3 flex items-center gap-2.5">
        <span className="w-2.5 h-2.5 rounded-full bg-teal-500" aria-hidden />
        <p className="text-sm text-teal-900">
          <span className="font-semibold">PhysioNet Mode Active.</span> This interpretation is generated from signal-first pipeline output.
        </p>
      </div>

      {/* ── Primary rhythm ────────────────────────────────────────────── */}
      <div className={`rounded-xl border px-5 py-4 flex items-start justify-between gap-4 ${ringBg}`}>
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
            Primary Rhythm
          </p>
          <h2 className="text-xl font-bold text-[var(--academy-ink)] leading-tight">{result.primary_rhythm}</h2>
          {result.differentials.length > 0 && (
            <p className="text-xs text-[var(--academy-muted)] mt-1.5">
              Also consider: {result.differentials.join(", ")}
            </p>
          )}
        </div>
        <div className="shrink-0 text-right">
          <div className={`text-3xl font-bold ${ringColor}`}>{overallPct}%</div>
          <div className="text-[10px] text-[var(--academy-muted)] mt-0.5">confidence</div>
        </div>
      </div>

      {/* ── Signal pipeline pre-classification ───────────────────────── */}
      {result.pipeline_classification && !result.pipeline_classification.error && (
        <PipelineClassificationBadge pc={result.pipeline_classification} />
      )}

      {/* ── Interpretation ────────────────────────────────────────────── */}
      <div className="rounded-xl border border-sky-100 bg-sky-50 px-4 py-3.5">
        <p className="text-[10px] font-bold uppercase tracking-widest text-sky-500 mb-1.5">
          Interpretation
        </p>
        <p className="text-sm text-[var(--academy-ink)] leading-relaxed">{result.explanation}</p>
      </div>

      {/* ── Systematic analysis ───────────────────────────────────────── */}
      <div className="rounded-xl border border-[var(--academy-line)] bg-[var(--academy-paper)] shadow-sm overflow-hidden">
        <div className="px-4 py-3 border-b border-[var(--academy-line)] flex items-center justify-between">
          <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)]">
            Systematic Analysis
          </p>
          <span className="text-[10px] text-[var(--academy-muted)] font-medium opacity-60">10-step signal-first framework</span>
        </div>
        <div className="px-4 divide-y divide-[var(--academy-line)]">
          <Row label="1. Rate"
            value={`${result.rate.bpm} bpm — ${result.rate.category}${result.rate.rr_intervals_ms?.length ? ` (RR: ${result.rate.rr_intervals_ms.join(", ")} ms)` : ""}`}
            confidence={result.rate.confidence}
          />
          <Row label="2. Rhythm"
            value={result.rhythm.regularity.replace(/_/g, " ")}
            confidence={result.rhythm.confidence}
          />
          <Row label="3. P Waves"
            value={
              result.p_waves.present
                ? `Present${result.p_waves.ratio ? ` (${result.p_waves.ratio})` : ""}${result.p_waves.morphology ? ` — ${result.p_waves.morphology}` : ""}`
                : "Absent"
            }
            confidence={result.p_waves.confidence}
          />
          <Row label="4. PR Interval"
            value={
              result.pr_interval.ms !== null
                ? `${result.pr_interval.ms} ms — ${result.pr_interval.normal ? "normal" : "abnormal"}, ${result.pr_interval.fixed ? "fixed" : "variable"}${result.pr_interval.measured_beats?.length ? ` (${result.pr_interval.measured_beats.join(", ")} ms)` : ""}`
                : null
            }
            confidence={result.pr_interval.confidence}
          />
          <Row label="5-6. QRS"
            value={
              result.qrs.duration_ms !== null
                ? `${result.qrs.duration_ms} ms — ${result.qrs.wide ? "wide" : "narrow"}${result.qrs.morphology ? ` (${result.qrs.morphology})` : ""}${result.qrs.measured_beats_ms?.length ? ` [${result.qrs.measured_beats_ms.join(", ")} ms]` : ""}`
                : null
            }
            confidence={result.qrs.confidence}
          />
          <Row label="7. ST Segment"
            value={
              result.st_segment.elevation
                ? `Elevation${result.st_segment.details ? ` — ${result.st_segment.details}` : ""}`
                : result.st_segment.depression
                ? `Depression${result.st_segment.details ? ` — ${result.st_segment.details}` : ""}`
                : `Isoelectric${result.st_segment.details ? ` — ${result.st_segment.details}` : ""}`
            }
            confidence={result.st_segment.confidence}
          />
          <Row label="8. T Waves"
            value={result.t_waves.morphology}
            confidence={result.t_waves.confidence}
          />
          <Row label="9. QTc"
            value={
              result.qtc.ms !== null
                ? `${result.qtc.ms} ms${result.qtc.prolonged !== null ? ` — ${result.qtc.prolonged ? "prolonged" : "normal"}` : ""}${result.qtc.measured_qt_ms?.length ? ` (QT: ${result.qtc.measured_qt_ms.join(", ")} ms)` : ""}`
                : null
            }
            confidence={result.qtc.confidence}
          />
          <Row label="10. Impression"
            value={result.primary_rhythm}
            confidence={result.overall_confidence}
          />
        </div>
      </div>

      {/* ── Caveats ───────────────────────────────────────────────────── */}
      {(result.caveats || result.image_quality !== "good") && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3.5 flex items-start gap-3">
          <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
          </svg>
          <div>
            <p className="text-xs font-semibold text-amber-800">
              Image quality:{" "}
              <span className={IMAGE_QUALITY_COLOR[result.image_quality] ?? "text-amber-700"}>
                {result.image_quality}
              </span>
            </p>
            {result.caveats && (
              <p className="text-xs text-amber-700 mt-0.5 leading-relaxed">{result.caveats}</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
