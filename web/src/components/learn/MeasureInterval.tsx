"use client";

import { useState, useRef, useCallback } from "react";

type IntervalType = "PR" | "QT";

interface Props {
  stripId: string;
  intervalType: IntervalType;
  imagePath?: string;
  /**
   * Expected range in ms at 25 mm/s (each small box = 40 ms).
   * Used to evaluate if the measurement is plausible.
   */
  normalRange?: [number, number];
}

/**
 * Simple drag-to-measure caliper tool.
 * User clicks and drags across the strip; the component estimates the interval
 * in ms assuming 25 mm/s paper speed and a standard strip width.
 *
 * Assumes full strip width ≈ 10 seconds (common for rhythm strips).
 */
export default function MeasureInterval({
  stripId,
  intervalType,
  imagePath,
  normalRange,
}: Props) {
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const src = imagePath ?? `/cases/${stripId}.png`;

  // Strip = 10 seconds wide → 10 000 ms total
  const STRIP_DURATION_MS = 10_000;

  const relativeX = useCallback((clientX: number): number => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return 0;
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  }, []);

  function onMouseDown(e: React.MouseEvent) {
    e.preventDefault();
    const rx = relativeX(e.clientX);
    setDragStart(rx);
    setDragEnd(rx);
    setIsDragging(true);
  }

  function onMouseMove(e: React.MouseEvent) {
    if (!isDragging) return;
    setDragEnd(relativeX(e.clientX));
  }

  function onMouseUp(e: React.MouseEvent) {
    if (!isDragging) return;
    setDragEnd(relativeX(e.clientX));
    setIsDragging(false);
  }

  function onTouchStart(e: React.TouchEvent) {
    const touch = e.touches[0];
    const rx = relativeX(touch.clientX);
    setDragStart(rx);
    setDragEnd(rx);
    setIsDragging(true);
  }

  function onTouchMove(e: React.TouchEvent) {
    if (!isDragging) return;
    setDragEnd(relativeX(e.touches[0].clientX));
  }

  function onTouchEnd(e: React.TouchEvent) {
    if (!isDragging) return;
    setDragEnd(relativeX(e.changedTouches[0].clientX));
    setIsDragging(false);
  }

  function handleReset() {
    setDragStart(null);
    setDragEnd(null);
  }

  const measuredMs =
    dragStart !== null && dragEnd !== null
      ? Math.round(Math.abs(dragEnd - dragStart) * STRIP_DURATION_MS)
      : null;

  const left = dragStart !== null && dragEnd !== null ? Math.min(dragStart, dragEnd) : null;
  const right = dragStart !== null && dragEnd !== null ? Math.max(dragStart, dragEnd) : null;

  let evaluation: "normal" | "abnormal" | "unknown" = "unknown";
  if (measuredMs !== null && normalRange) {
    evaluation =
      measuredMs >= normalRange[0] && measuredMs <= normalRange[1]
        ? "normal"
        : "abnormal";
  }

  const NORMAL_RANGES: Record<IntervalType, string> = {
    PR: "120–200 ms",
    QT: "360–440 ms (QTc)",
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-700">
          Drag across the{" "}
          <span className="text-sky-600 font-semibold">{intervalType} interval</span>{" "}
          to measure it.
        </p>
        <span className="text-xs text-slate-400">Normal: {NORMAL_RANGES[intervalType]}</span>
      </div>

      {/* Strip + calipers */}
      <div
        ref={containerRef}
        className="relative select-none cursor-col-resize overflow-hidden rounded-lg border border-slate-200 touch-none"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={() => setIsDragging(false)}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        role="img"
        aria-label={`EKG strip — drag to measure ${intervalType} interval`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={`EKG strip for ${stripId}`}
          className="w-full object-contain pointer-events-none"
          draggable={false}
        />

        {/* Shaded selection */}
        {left !== null && right !== null && (
          <div
            className="absolute top-0 bottom-0 pointer-events-none"
            style={{
              left: `${left * 100}%`,
              width: `${(right - left) * 100}%`,
              background: "rgba(14,165,233,0.18)",
              borderLeft: "2px solid #0ea5e9",
              borderRight: "2px solid #0ea5e9",
            }}
          />
        )}
      </div>

      {/* Result */}
      {measuredMs !== null && (
        <div
          className={`flex items-center gap-3 rounded-lg px-3 py-2 border text-sm font-medium ${
            evaluation === "normal"
              ? "bg-emerald-50 border-emerald-200 text-emerald-700"
              : evaluation === "abnormal"
              ? "bg-amber-50 border-amber-200 text-amber-700"
              : "bg-slate-50 border-slate-200 text-slate-700"
          }`}
        >
          <span className="text-2xl font-bold tabular-nums">
            {measuredMs} ms
          </span>
          {evaluation === "normal" && <span>— within normal range</span>}
          {evaluation === "abnormal" && <span>— outside normal range</span>}
          {evaluation === "unknown" && <span>measured</span>}

          <button
            onClick={handleReset}
            className="ml-auto text-xs underline opacity-60 hover:opacity-100"
          >
            Clear
          </button>
        </div>
      )}

      <p className="text-xs text-slate-400">
        Assumes 25 mm/s paper speed. Strip represents ~10 seconds. For teaching purposes only.
      </p>
    </div>
  );
}
