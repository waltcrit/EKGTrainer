"use client";

import { useEffect, useState } from "react";
import { SYSTEMATIC_STEPS, type SystematicStep } from "@/lib/learn/systematic";

const STORAGE_KEY_PREFIX = "ekg_checklist_";

interface Props {
  /**
   * Optional strip ID to scope checklist state per case.
   * If omitted, uses a global key.
   */
  stripId?: string;
  /** Show in compact (sidebar) mode or full-width lesson mode. */
  compact?: boolean;
}

export default function SystematicChecklist({ stripId, compact = false }: Props) {
  const storageKey = `${STORAGE_KEY_PREFIX}${stripId ?? "global"}`;

  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [mounted, setMounted] = useState(false);

  // Hydrate from localStorage after mount (avoids SSR mismatch)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setChecked(new Set(JSON.parse(raw) as string[]));
      }
    } catch {
      // ignore
    }
    setMounted(true);
  }, [storageKey]);

  function toggle(id: string) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      try {
        localStorage.setItem(storageKey, JSON.stringify([...next]));
      } catch {
        // ignore
      }
      return next;
    });
  }

  function reset() {
    setChecked(new Set());
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }

  const completedCount = checked.size;
  const totalCount = SYSTEMATIC_STEPS.length;
  const allDone = completedCount === totalCount;
  const progressClass =
    !mounted || totalCount === 0
      ? "w-0"
      : completedCount >= totalCount
        ? "w-full"
        : completedCount >= totalCount * 0.75
          ? "w-3/4"
          : completedCount >= totalCount * 0.5
            ? "w-1/2"
            : completedCount >= totalCount * 0.25
              ? "w-1/4"
              : "w-0";

  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white shadow-sm ${
        compact ? "p-3" : "p-5"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3
            className={`font-semibold text-slate-800 ${
              compact ? "text-sm" : "text-base"
            }`}
          >
            Systematic EKG Read
          </h3>
          {!compact && (
            <p className="text-xs text-slate-500 mt-0.5">
              Check off each step as you work through the strip.
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`tabular-nums font-mono text-xs px-2 py-0.5 rounded-full border ${
              allDone
                ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                : "bg-slate-50 border-slate-200 text-slate-500"
            }`}
          >
            {mounted ? completedCount : 0}/{totalCount}
          </span>
          {mounted && completedCount > 0 && (
            <button
              onClick={reset}
              className="text-xs text-slate-400 hover:text-slate-600 underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 bg-slate-100 rounded-full mb-3 overflow-hidden">
        <div
          className={`${progressClass} h-full bg-sky-500 rounded-full transition-all duration-300`}
        />
      </div>

      {/* Steps */}
      <ol className={`space-y-${compact ? "1" : "2"}`}>
        {SYSTEMATIC_STEPS.map((step: SystematicStep, idx: number) => {
          const isChecked = mounted && checked.has(step.id);
          return (
            <li key={step.id}>
              <button
                onClick={() => toggle(step.id)}
                className={`w-full flex items-start gap-2.5 rounded-lg text-left transition-colors ${
                  compact ? "px-2 py-1.5" : "px-3 py-2"
                } ${
                  isChecked
                    ? "bg-emerald-50 hover:bg-emerald-100"
                    : "hover:bg-slate-50"
                }`}
              >
                {/* Checkbox */}
                <span
                  className={`mt-0.5 flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                    isChecked
                      ? "border-emerald-500 bg-emerald-500"
                      : "border-slate-300 bg-white"
                  }`}
                >
                  {isChecked && (
                    <svg
                      className="w-3 h-3 text-white"
                      viewBox="0 0 12 12"
                      fill="none"
                      aria-hidden
                    >
                      <path
                        d="M2 6l3 3 5-5"
                        stroke="currentColor"
                        strokeWidth={2}
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                </span>

                {/* Step content */}
                <div className="min-w-0">
                  <span
                    className={`font-medium leading-tight ${
                      compact ? "text-xs" : "text-sm"
                    } ${isChecked ? "text-emerald-700 line-through decoration-emerald-400" : "text-slate-700"}`}
                  >
                    <span className="text-slate-400 font-mono mr-1">{idx + 1}.</span>
                    {step.title}
                  </span>
                  {!compact && (
                    <p
                      className={`text-xs mt-0.5 ${
                        isChecked ? "text-emerald-600" : "text-slate-500"
                      }`}
                    >
                      {step.description}
                    </p>
                  )}
                </div>
              </button>
            </li>
          );
        })}
      </ol>

      {/* Done state */}
      {mounted && allDone && (
        <div className="mt-3 rounded-lg bg-emerald-50 border border-emerald-200 px-3 py-2 text-center">
          <p className="text-sm font-semibold text-emerald-700">
            All steps complete - great systematic read!
          </p>
        </div>
      )}
    </div>
  );
}
