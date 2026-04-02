"use client";

import { useState, useRef } from "react";

interface Props {
  /** Case ID — image loaded from /cases/{stripId}_strip.png or similar */
  stripId: string;
  /**
   * Correct region as fraction of image width [left, right].
   * Default: first third of the strip where P waves appear.
   */
  correctRegion?: [number, number];
  imagePath?: string;
}

type Feedback = "idle" | "correct" | "incorrect";

/**
 * Shows a rhythm strip and asks the user to click where the P wave is.
 * Gives simple correct/incorrect feedback based on x-position.
 */
export default function IdentifyPWave({
  stripId,
  correctRegion = [0.05, 0.35],
  imagePath,
}: Props) {
  const [feedback, setFeedback] = useState<Feedback>("idle");
  const [clickX, setClickX] = useState<number | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const src = imagePath ?? `/cases/${stripId}.png`;

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = (e.clientX - rect.left) / rect.width;
    setClickX(relX);

    const [lo, hi] = correctRegion;
    setFeedback(relX >= lo && relX <= hi ? "correct" : "incorrect");
  }

  function handleReset() {
    setFeedback("idle");
    setClickX(null);
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-3">
      <p className="text-sm font-medium text-slate-700">
        Click on a <span className="text-sky-600 font-semibold">P wave</span> in the strip below.
      </p>

      <div
        className="relative cursor-crosshair select-none overflow-hidden rounded-lg border border-slate-200"
        onClick={feedback === "idle" ? handleClick : undefined}
        role="button"
        aria-label="EKG strip — click to identify a P wave"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={imgRef}
          src={src}
          alt={`EKG strip for ${stripId}`}
          className="w-full object-contain"
          draggable={false}
        />

        {/* Click marker */}
        {clickX !== null && (
          <div
            className="absolute top-0 bottom-0 w-0.5 pointer-events-none"
            style={{
              left: `${clickX * 100}%`,
              background: feedback === "correct" ? "#22c55e" : "#ef4444",
            }}
          />
        )}
      </div>

      {/* Feedback */}
      {feedback === "correct" && (
        <div className="flex items-start gap-2 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2">
          <span className="text-emerald-600 text-base">✓</span>
          <p className="text-sm text-emerald-700 font-medium">
            Correct! That region contains the P wave — the small positive deflection before the QRS complex.
          </p>
        </div>
      )}
      {feedback === "incorrect" && (
        <div className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 px-3 py-2">
          <span className="text-red-500 text-base">✗</span>
          <p className="text-sm text-red-700 font-medium">
            Not quite. Look for the small, rounded bump just before the tall QRS spike. Try again!
          </p>
        </div>
      )}

      {feedback !== "idle" && (
        <button
          onClick={handleReset}
          className="text-xs text-slate-500 underline hover:text-slate-700"
        >
          Try again
        </button>
      )}
    </div>
  );
}
