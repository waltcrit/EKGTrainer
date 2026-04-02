"use client";

import { useState, useRef, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

type DragState = "idle" | "dragging";
type EvalState = "correct" | "close" | "incorrect";
type FeedbackState = DragState | EvalState;

interface Props {
  /** Case ID — used to derive imagePath when imagePath is omitted */
  stripId: string;
  /** Explicit image path. Defaults to /cases/{stripId}.png */
  imagePath?: string;
  /**
   * True QT start as a fraction of strip width [0, 1].
   * Corresponds to the onset of the QRS complex in the first visible beat.
   */
  trueStart: number;
  /**
   * True QT end as a fraction of strip width [0, 1].
   * Corresponds to the end of the T wave in the same beat.
   */
  trueEnd: number;
  /**
   * Acceptance tolerance as a fraction of strip width.
   * A value of 0.04 means the user's boundary must be within 4% of the strip
   * width of the true boundary (≈40 ms on a standard 10-second strip).
   * Default: 0.04.
   */
  tolerance?: number;
  /**
   * Assumed total strip duration in ms. Used only for displaying the
   * measured value to the learner. Default: 10 000 ms.
   */
  stripDurationMs?: number;
}

// ── Pure evaluation function (exported for testing) ──────────────────────────

/**
 * Determines whether the user's drag selection correctly identifies the
 * QT interval boundaries within the given tolerance.
 *
 * @param userStart  - Left boundary of user selection [0, 1]
 * @param userEnd    - Right boundary of user selection [0, 1]
 * @param trueStart  - True QT onset [0, 1]
 * @param trueEnd    - True QT end [0, 1]
 * @param tolerance  - Acceptable error per boundary [0, 1]
 * @returns "correct" | "close" | "incorrect"
 *
 * Rules:
 *   - Normalise user selection so left < right regardless of drag direction.
 *   - "correct"   → both boundaries within tolerance of their true values.
 *   - "close"     → exactly one boundary within tolerance.
 *   - "incorrect" → neither boundary within tolerance.
 */
export function evaluateQTSelection(
  userStart: number,
  userEnd: number,
  trueStart: number,
  trueEnd: number,
  tolerance: number
): EvalState {
  const selLeft = Math.min(userStart, userEnd);
  const selRight = Math.max(userStart, userEnd);

  const startOk = Math.abs(selLeft - trueStart) <= tolerance;
  const endOk = Math.abs(selRight - trueEnd) <= tolerance;

  if (startOk && endOk) return "correct";
  if (startOk || endOk) return "close";
  return "incorrect";
}

// ── Visual config keyed by feedback state ─────────────────────────────────────

const OVERLAY_BG: Record<FeedbackState, string> = {
  idle: "rgba(14,165,233,0.16)",
  dragging: "rgba(14,165,233,0.22)",
  correct: "rgba(16,185,129,0.22)",
  close: "rgba(245,158,11,0.22)",
  incorrect: "rgba(239,68,68,0.18)",
};

const OVERLAY_BORDER: Record<FeedbackState, string> = {
  idle: "#0ea5e9",
  dragging: "#0ea5e9",
  correct: "#10b981",
  close: "#f59e0b",
  incorrect: "#ef4444",
};

type FeedbackBannerConfig = {
  bg: string;
  border: string;
  text: string;
  icon: React.ReactNode;
  heading: string;
  detail: string;
};

const BANNER: Record<EvalState, FeedbackBannerConfig> = {
  correct: {
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    text: "text-emerald-800",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" aria-hidden>
        <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm3.857-9.809a.75.75 0 0 0-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 1 0-1.06 1.061l2.5 2.5a.75.75 0 0 0 1.137-.089l4-5.5Z" clipRule="evenodd" />
      </svg>
    ),
    heading: "Correct!",
    detail: "Both boundaries match the QT interval.",
  },
  close: {
    bg: "bg-amber-50",
    border: "border-amber-200",
    text: "text-amber-800",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" aria-hidden>
        <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495ZM10 5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 5Zm0 9a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" clipRule="evenodd" />
      </svg>
    ),
    heading: "Almost there",
    detail: "One boundary is off. The QT starts at the first deflection of the QRS and ends where the T wave returns to the isoelectric line.",
  },
  incorrect: {
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-800",
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-red-500 shrink-0 mt-0.5" aria-hidden>
        <path fillRule="evenodd" d="M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16ZM8.28 7.22a.75.75 0 0 0-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 1 0 1.06 1.06L10 11.06l1.72 1.72a.75.75 0 1 0 1.06-1.06L11.06 10l1.72-1.72a.75.75 0 0 0-1.06-1.06L10 8.94 8.28 7.22Z" clipRule="evenodd" />
      </svg>
    ),
    heading: "Not quite",
    detail: "The QT interval runs from the very start of the QRS complex to the point where the T wave meets the baseline. Try again.",
  },
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function QTIntervalDrag({
  stripId,
  imagePath,
  trueStart,
  trueEnd,
  tolerance = 0.04,
  stripDurationMs = 10_000,
}: Props) {
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState>("idle");
  const containerRef = useRef<HTMLDivElement>(null);

  const src = imagePath ?? `/cases/${stripId}.png`;

  // ── Coordinate helpers ──────────────────────────────────────────────────────

  const toRelativeX = useCallback((clientX: number): number => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return 0;
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
  }, []);

  // ── Drag lifecycle ──────────────────────────────────────────────────────────

  function beginDrag(rx: number) {
    setDragStart(rx);
    setDragEnd(rx);
    setIsDragging(true);
    setFeedback("dragging");
  }

  function moveDrag(rx: number) {
    if (!isDragging) return;
    setDragEnd(rx);
  }

  function commitDrag(rx: number) {
    if (!isDragging) return;
    const start = dragStart ?? rx;
    setDragEnd(rx);
    setIsDragging(false);

    // Only evaluate if the user dragged a meaningful distance (> 1% of strip).
    if (Math.abs(rx - start) < 0.01) {
      setFeedback("idle");
      setDragStart(null);
      setDragEnd(null);
      return;
    }

    setFeedback(evaluateQTSelection(start, rx, trueStart, trueEnd, tolerance));
  }

  function handleReset() {
    setDragStart(null);
    setDragEnd(null);
    setFeedback("idle");
  }

  // ── Derived values ──────────────────────────────────────────────────────────

  const overlayLeft =
    dragStart !== null && dragEnd !== null
      ? Math.min(dragStart, dragEnd)
      : null;
  const overlayRight =
    dragStart !== null && dragEnd !== null
      ? Math.max(dragStart, dragEnd)
      : null;

  const measuredMs =
    overlayLeft !== null && overlayRight !== null
      ? Math.round((overlayRight - overlayLeft) * stripDurationMs)
      : null;

  const evalState =
    feedback !== "idle" && feedback !== "dragging"
      ? (feedback as EvalState)
      : null;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3 not-prose">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-700 leading-snug">
          Drag to select the{" "}
          <span className="font-semibold text-sky-600">QT interval</span>
          {" "}— from the onset of the QRS complex to the end of the T wave.
        </p>
        {feedback !== "idle" && (
          <button
            onClick={handleReset}
            className="shrink-0 text-xs text-slate-400 underline underline-offset-2 hover:text-slate-600 transition-colors"
          >
            Reset
          </button>
        )}
      </div>

      {/* EKG strip + drag overlay */}
      <div
        ref={containerRef}
        className="relative select-none cursor-col-resize overflow-hidden rounded-lg border border-slate-200 touch-none bg-[#fff8f0]"
        onMouseDown={(e) => { e.preventDefault(); beginDrag(toRelativeX(e.clientX)); }}
        onMouseMove={(e) => moveDrag(toRelativeX(e.clientX))}
        onMouseUp={(e) => commitDrag(toRelativeX(e.clientX))}
        onMouseLeave={() => {
          if (isDragging) commitDrag(dragEnd ?? dragStart ?? 0);
        }}
        onTouchStart={(e) => { e.preventDefault(); beginDrag(toRelativeX(e.touches[0].clientX)); }}
        onTouchMove={(e) => { e.preventDefault(); moveDrag(toRelativeX(e.touches[0].clientX)); }}
        onTouchEnd={(e) => { commitDrag(toRelativeX(e.changedTouches[0].clientX)); }}
        role="img"
        aria-label={`EKG strip — drag to select the QT interval`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={`EKG strip ${stripId}`}
          className="w-full object-contain pointer-events-none"
          draggable={false}
        />

        {/* Shaded selection overlay */}
        {overlayLeft !== null && overlayRight !== null && (
          <div
            className="absolute top-0 bottom-0 pointer-events-none"
            style={{
              left: `${overlayLeft * 100}%`,
              width: `${(overlayRight - overlayLeft) * 100}%`,
              background: OVERLAY_BG[feedback],
              borderLeft: `2px solid ${OVERLAY_BORDER[feedback]}`,
              borderRight: `2px solid ${OVERLAY_BORDER[feedback]}`,
              transition: "background 0.15s, border-color 0.15s",
            }}
          />
        )}
      </div>

      {/* Live measurement during drag */}
      {feedback === "dragging" && measuredMs !== null && (
        <p className="text-xs text-slate-500 tabular-nums">
          Selection: <span className="font-semibold text-slate-700">{measuredMs} ms</span>
          <span className="ml-2 opacity-60">— release to check</span>
        </p>
      )}

      {/* Evaluation banner (shown after drag completes) */}
      {evalState !== null && (
        <div
          className={`flex items-start gap-3 rounded-lg border px-3 py-3 text-sm ${BANNER[evalState].bg} ${BANNER[evalState].border} ${BANNER[evalState].text}`}
          role="alert"
        >
          {BANNER[evalState].icon}
          <div className="flex-1 min-w-0">
            <p className="font-semibold leading-snug">{BANNER[evalState].heading}</p>
            <p className="mt-0.5 font-normal opacity-80 leading-snug">
              {BANNER[evalState].detail}
            </p>
            {measuredMs !== null && (
              <p className="mt-1 text-xs opacity-60 tabular-nums">
                You measured: ~{measuredMs} ms
                {evalState === "correct" && " — within the normal QTc range (360–440 ms)"}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Idle hint */}
      {feedback === "idle" && (
        <p className="text-xs text-slate-400">
          Click and drag to mark your selection. The QT interval represents total ventricular
          electrical systole (depolarization + repolarization).
        </p>
      )}
    </div>
  );
}
