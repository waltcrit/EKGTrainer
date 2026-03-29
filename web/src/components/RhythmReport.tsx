"use client";

import type { EKGAnalysisResult } from "@/types/analysis";

interface RhythmReportProps {
  result: EKGAnalysisResult;
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 80 ? "bg-green-100 text-green-800" :
    pct >= 60 ? "bg-yellow-100 text-yellow-800" :
                "bg-red-100 text-red-800";
  return (
    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${color}`}>
      {pct}%
    </span>
  );
}

function Row({ label, value, confidence }: { label: string; value: string | null; confidence?: number }) {
  return (
    <div className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500 w-36 shrink-0">{label}</span>
      <span className="text-sm font-medium text-gray-900 flex-1">{value ?? "—"}</span>
      {confidence !== undefined && <ConfidenceBadge value={confidence} />}
    </div>
  );
}

export default function RhythmReport({ result }: RhythmReportProps) {
  const overallPct = Math.round(result.overall_confidence * 100);
  const ringColor =
    overallPct >= 80 ? "text-green-500" :
    overallPct >= 60 ? "text-yellow-500" :
                       "text-red-500";

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col gap-4">
      {/* Primary rhythm banner */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-gray-400 mb-1">Primary Rhythm</p>
            <h2 className="text-2xl font-bold text-gray-900">{result.primary_rhythm}</h2>
            {result.differentials.length > 0 && (
              <p className="text-sm text-gray-500 mt-1">
                Also consider: {result.differentials.join(", ")}
              </p>
            )}
          </div>
          <div className={`text-4xl font-bold ${ringColor}`}>
            {overallPct}%
          </div>
        </div>
      </div>

      {/* Explanation */}
      <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p className="text-sm font-medium text-blue-900 mb-1">Interpretation</p>
        <p className="text-sm text-blue-800 leading-relaxed">{result.explanation}</p>
      </div>

      {/* 9-step parameter grid */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <p className="text-xs uppercase tracking-wider text-gray-400 mb-3">Systematic Analysis</p>
        <Row
          label="Rate"
          value={`${result.rate.bpm} bpm — ${result.rate.category}${result.rate.rr_intervals_ms?.length ? ` (RR: ${result.rate.rr_intervals_ms.join(", ")} ms)` : ""}`}
          confidence={result.rate.confidence}
        />
        <Row
          label="Rhythm"
          value={result.rhythm.regularity.replace(/_/g, " ")}
          confidence={result.rhythm.confidence}
        />
        <Row
          label="P Waves"
          value={
            result.p_waves.present
              ? `Present${result.p_waves.ratio ? ` (${result.p_waves.ratio})` : ""}${result.p_waves.morphology ? ` — ${result.p_waves.morphology}` : ""}`
              : "Absent"
          }
          confidence={result.p_waves.confidence}
        />
        <Row
          label="PR Interval"
          value={
            result.pr_interval.ms !== null
              ? `${result.pr_interval.ms} ms — ${result.pr_interval.normal ? "normal" : "abnormal"}, ${result.pr_interval.fixed ? "fixed" : "variable"}${result.pr_interval.measured_beats?.length ? ` (beats: ${result.pr_interval.measured_beats.join(", ")} ms)` : ""}`
              : null
          }
          confidence={result.pr_interval.confidence}
        />
        <Row
          label="QRS Duration"
          value={
            result.qrs.duration_ms !== null
              ? `${result.qrs.duration_ms} ms — ${result.qrs.wide ? "wide" : "narrow"}${result.qrs.morphology ? ` (${result.qrs.morphology})` : ""}${result.qrs.measured_beats_ms?.length ? ` [${result.qrs.measured_beats_ms.join(", ")} ms]` : ""}`
              : null
          }
          confidence={result.qrs.confidence}
        />
        <Row
          label="ST Segment"
          value={
            result.st_segment.elevation
              ? `Elevation${result.st_segment.details ? ` — ${result.st_segment.details}` : ""}`
              : result.st_segment.depression
              ? `Depression${result.st_segment.details ? ` — ${result.st_segment.details}` : ""}`
              : `Isoelectric${result.st_segment.details ? ` — ${result.st_segment.details}` : ""}`
          }
          confidence={result.st_segment.confidence}
        />
        <Row
          label="T Waves"
          value={result.t_waves.morphology}
          confidence={result.t_waves.confidence}
        />
        <Row
          label="QTc"
          value={
            result.qtc.ms !== null
              ? `${result.qtc.ms} ms${result.qtc.prolonged !== null ? ` — ${result.qtc.prolonged ? "prolonged" : "normal"}` : ""}${result.qtc.measured_qt_ms?.length ? ` (QT: ${result.qtc.measured_qt_ms.join(", ")} ms)` : ""}`
              : null
          }
          confidence={result.qtc.confidence}
        />
      </div>

      {/* Caveats / image quality */}
      {(result.caveats || result.image_quality !== "good") && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-800 mb-1">
            Image quality: {result.image_quality}
          </p>
          {result.caveats && (
            <p className="text-sm text-amber-700">{result.caveats}</p>
          )}
        </div>
      )}

      <p className="text-xs text-center text-gray-400">
        For educational use only. Not a substitute for clinical judgment.
      </p>
    </div>
  );
}
