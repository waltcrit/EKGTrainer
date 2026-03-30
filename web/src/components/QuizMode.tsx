"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EKGCase } from "@/types/cases";
import type { EKGAnalysisResult as AnalysisResult } from "@/types/analysis";
import RhythmReport from "./RhythmReport";

interface QuizModeProps {
  cases: EKGCase[];
}

type QuizState = "question" | "revealed" | "analyzing";

interface SessionStats {
  attempted: number;
  correct: number;
  byCategory: Record<string, { attempted: number; correct: number }>;
}

const ANSWER_LABELS = ["A", "B", "C", "D"] as const;

const DIFF_CONFIG: Record<number, { label: string; dot: string; text: string }> = {
  1: { label: "Foundational", dot: "bg-emerald-400", text: "text-emerald-700" },
  2: { label: "Intermediate", dot: "bg-sky-400",     text: "text-sky-700"     },
  3: { label: "Advanced",     dot: "bg-orange-400",  text: "text-orange-700"  },
  4: { label: "Expert",       dot: "bg-red-400",     text: "text-red-700"     },
};

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildChoices(correct: EKGCase, all: EKGCase[]): string[] {
  const sameCategory = all.filter((c) => c.id !== correct.id && c.category === correct.category);
  const other = all.filter((c) => c.id !== correct.id && c.category !== correct.category);
  const pool = shuffle([...sameCategory, ...other]);
  const wrong = Array.from(new Set(pool.map((c) => c.rhythm)))
    .filter((r) => r !== correct.rhythm)
    .slice(0, 3);
  return shuffle([correct.rhythm, ...wrong]);
}

export default function QuizMode({ cases }: QuizModeProps) {
  const [queue, setQueue]               = useState<EKGCase[]>(cases);
  const [index, setIndex]               = useState(0);
  const [state, setState]               = useState<QuizState>("question");
  const [selected, setSelected]         = useState<string | null>(null);
  const [showTwelveLead, setShowTwelveLead] = useState(false);
  const [aiResult, setAiResult]         = useState<AnalysisResult | null>(null);
  const [aiError, setAiError]           = useState<string | null>(null);
  const [stats, setStats]               = useState<SessionStats>({ attempted: 0, correct: 0, byCategory: {} });
  const [mounted, setMounted]           = useState(false);

  useEffect(() => { setQueue(shuffle(cases)); setMounted(true); }, [cases]);

  const current = queue[index % queue.length];
  const choices = useMemo(
    () => (mounted ? buildChoices(current, cases) : []),
    [current, cases, mounted]
  );
  const isCorrect = selected === current.rhythm;
  const diff = DIFF_CONFIG[current.difficulty];
  const accuracyPct = stats.attempted > 0
    ? Math.round((stats.correct / stats.attempted) * 100)
    : null;

  const handleSelect = (choice: string) => {
    if (state !== "question") return;
    setSelected(choice);
    setState("revealed");
    const correct = choice === current.rhythm;
    setStats((prev) => {
      const cat = prev.byCategory[current.category] ?? { attempted: 0, correct: 0 };
      return {
        attempted: prev.attempted + 1,
        correct: prev.correct + (correct ? 1 : 0),
        byCategory: { ...prev.byCategory, [current.category]: { attempted: cat.attempted + 1, correct: cat.correct + (correct ? 1 : 0) } },
      };
    });
  };

  const handleAIAnalysis = async () => {
    setState("analyzing");
    setAiResult(null);
    setAiError(null);
    try {
      const resp = await fetch(current.imagePath);
      const blob = await resp.blob();
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve((reader.result as string).split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ imageBase64: base64, mediaType: "image/png" }),
      });
      const data = await res.json();
      if (data.success) setAiResult(data.result);
      else setAiError(data.error ?? "Analysis failed");
    } catch (e) {
      setAiError(e instanceof Error ? e.message : "Network error");
    }
    setState("revealed");
  };

  const handleNext = () => {
    setIndex((i) => i + 1);
    setState("question");
    setSelected(null);
    setAiResult(null);
    setAiError(null);
    setShowTwelveLead(false);
  };

  if (!mounted) return null;

  const showingTwelveLead = showTwelveLead || state === "revealed" || state === "analyzing";

  return (
    <div className="flex flex-col gap-4">

      {/* ── Case header ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${diff.dot}`} />
          <span className={`text-xs font-semibold ${diff.text}`}>{diff.label}</span>
        </div>
        {stats.attempted > 0 && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <span className="font-semibold text-slate-700">{stats.correct}</span>
              <span>/</span>
              <span>{stats.attempted}</span>
            </div>
            <div className="w-20 h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  (accuracyPct ?? 0) >= 80 ? "bg-emerald-500" :
                  (accuracyPct ?? 0) >= 60 ? "bg-amber-400"  : "bg-red-400"
                }`}
                style={{ width: `${accuracyPct ?? 0}%` }}
              />
            </div>
            <span className="font-medium">{accuracyPct}%</span>
          </div>
        )}
      </div>

      {/* ── EKG image ──────────────────────────────────────────────────── */}
      <div className="rounded-xl overflow-hidden border border-slate-200 shadow-sm bg-[#fff5e6]">
        <img
          key={showingTwelveLead ? current.twelveleadPath : current.imagePath}
          src={showingTwelveLead ? current.twelveleadPath : current.imagePath}
          alt={showingTwelveLead ? "12-lead EKG" : "EKG rhythm strip"}
          className="w-full object-contain"
        />
        {/* Image type label */}
        <div className="px-3 py-1.5 flex items-center justify-between bg-[#fff5e6] border-t border-[#ffe4b8]">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-700/60">
            {showingTwelveLead ? "12-Lead EKG" : "Rhythm Strip — Lead II"}
          </span>
          {state === "revealed" && (
            <span className="text-[10px] text-amber-700/50">Teaching view</span>
          )}
        </div>
      </div>

      {/* ── 12-lead request (question phase only) ──────────────────────── */}
      {state === "question" && !showTwelveLead && (
        <button
          onClick={() => setShowTwelveLead(true)}
          className="flex items-center justify-center gap-2 w-full rounded-lg border border-slate-200
                     bg-white py-2.5 text-sm font-medium text-slate-600
                     hover:border-slate-300 hover:bg-slate-50 hover:text-slate-800
                     transition-all duration-150 shadow-sm group"
        >
          <svg className="w-4 h-4 text-slate-400 group-hover:text-sky-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Request 12-lead EKG
        </button>
      )}

      {/* ── Answer choices (question phase) ────────────────────────────── */}
      {state === "question" && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-0.5 px-0.5">
            Identify the rhythm
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {choices.map((choice, i) => (
              <button
                key={choice}
                onClick={() => handleSelect(choice)}
                className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white
                           px-4 py-3.5 text-sm font-medium text-slate-700 text-left
                           hover:border-sky-300 hover:bg-sky-50 hover:text-sky-900
                           active:scale-[0.99] transition-all duration-100 shadow-sm"
              >
                <span className="w-6 h-6 rounded bg-slate-100 text-slate-500 text-xs font-bold
                                 flex items-center justify-center shrink-0">
                  {ANSWER_LABELS[i]}
                </span>
                {choice}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Revealed / teaching phase ───────────────────────────────────── */}
      {(state === "revealed" || state === "analyzing") && (
        <div className="flex flex-col gap-3">

          {/* Answer choices — locked, color-coded */}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {choices.map((choice, i) => {
              const isAnswer   = choice === current.rhythm;
              const isSelected = choice === selected;
              const isDimmed   = !isAnswer && !isSelected;

              let containerCls = "flex items-center gap-3 rounded-lg border px-4 py-3.5 text-sm font-medium text-left cursor-default";
              let labelCls = "w-6 h-6 rounded text-xs font-bold flex items-center justify-center shrink-0";

              if (isAnswer) {
                containerCls += " border-emerald-300 bg-emerald-50 text-emerald-800";
                labelCls     += " bg-emerald-500 text-white";
              } else if (isSelected) {
                containerCls += " border-red-300 bg-red-50 text-red-800";
                labelCls     += " bg-red-500 text-white";
              } else if (isDimmed) {
                containerCls += " border-slate-100 bg-slate-50 text-slate-400 opacity-60";
                labelCls     += " bg-slate-200 text-slate-400";
              }

              return (
                <div key={choice} className={containerCls}>
                  <span className={labelCls}>{ANSWER_LABELS[i]}</span>
                  {choice}
                  {isAnswer && (
                    <svg className="w-4 h-4 ml-auto text-emerald-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                  {isSelected && !isAnswer && (
                    <svg className="w-4 h-4 ml-auto text-red-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              );
            })}
          </div>

          {/* Result banner */}
          <div className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
            isCorrect
              ? "bg-emerald-50 border-emerald-200"
              : "bg-red-50 border-red-200"
          }`}>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
              isCorrect ? "bg-emerald-500" : "bg-red-500"
            }`}>
              {isCorrect
                ? <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" /></svg>
                : <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
              }
            </div>
            <div>
              <p className={`font-semibold text-sm ${isCorrect ? "text-emerald-900" : "text-red-900"}`}>
                {isCorrect ? "Correct" : `Incorrect — this is ${current.rhythm}`}
              </p>
              {!isCorrect && selected && (
                <p className="text-xs text-red-600 mt-0.5">You selected: {selected}</p>
              )}
            </div>
          </div>

          {/* Teaching panel */}
          <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100 shadow-sm overflow-hidden">
            {/* Key features */}
            <div className="px-4 py-3.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2.5">
                Key Features
              </p>
              <ul className="flex flex-col gap-1.5">
                {current.keyFeatures.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
                    <svg className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            {/* Teaching point */}
            <div className="px-4 py-3.5 bg-sky-50">
              <p className="text-[10px] font-bold uppercase tracking-widest text-sky-500 mb-1.5">
                Teaching Point
              </p>
              <p className="text-sm text-slate-700 leading-relaxed">{current.teaching}</p>
            </div>

            {/* Meta row */}
            <div className="px-4 py-2.5 flex items-center gap-4 text-xs text-slate-400 bg-slate-50">
              {current.rate !== null && current.rate > 0 && (
                <span>Rate <span className="font-semibold text-slate-600">{current.rate} bpm</span></span>
              )}
              <span>Rhythm <span className="font-semibold text-slate-600">{current.regularity.replace(/_/g, " ")}</span></span>
            </div>
          </div>

          {/* AI analysis */}
          {!aiResult && !aiError && state !== "analyzing" && (
            <button
              onClick={handleAIAnalysis}
              className="flex items-center justify-center gap-2 w-full rounded-lg border border-slate-200
                         bg-white py-2.5 text-sm font-medium text-slate-600
                         hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700
                         transition-all duration-150 shadow-sm group"
            >
              <svg className="w-4 h-4 text-slate-400 group-hover:text-sky-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
              </svg>
              Get AI 9-step analysis
            </button>
          )}

          {state === "analyzing" && (
            <div className="flex items-center justify-center gap-2.5 py-3 text-sm text-slate-500">
              <svg className="w-4 h-4 animate-spin text-sky-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing…
            </div>
          )}

          {aiError && (
            <p className="text-sm text-red-500 text-center">{aiError}</p>
          )}

          {aiResult && <RhythmReport result={aiResult} />}

          {/* Next button */}
          <button
            onClick={handleNext}
            className="w-full rounded-lg bg-slate-900 text-white py-3 text-sm font-semibold
                       hover:bg-slate-700 active:bg-slate-800 transition-colors duration-150
                       flex items-center justify-center gap-2"
          >
            Next case
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
