"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { EKGCase, RhythmCategory } from "@/types/cases";
import { CATEGORY_LABELS } from "@/types/cases";
import type { EKGAnalysisResult as AnalysisResult } from "@/types/analysis";
import RhythmReport from "./RhythmReport";

interface QuizModeProps {
  initialCaseId?: string | null;
}

type QuizState = "question" | "revealed" | "analyzing";
type DiagnosisScope = "all" | "selected";

interface SessionStats {
  attempted: number;
  correct: number;
  byCategory: Record<string, { attempted: number; correct: number }>;
}

interface QuizQuestion {
  opaqueId: string;
  difficulty: 1 | 2 | 3 | 4;
  category: RhythmCategory;
  imageUrl: string;
  twelveLeadUrl: string;
  rate: number | null;
  regularity: "regular" | "regularly_irregular" | "irregularly_irregular" | "chaotic" | "none";
  choices: string[];
}

interface QuizReveal {
  correct: boolean;
  correctRhythm: string;
  keyFeatures: string[];
  teaching: string;
  rate: number | null;
  regularity: "regular" | "regularly_irregular" | "irregularly_irregular" | "chaotic" | "none";
}

interface QuizMeta {
  totalCases: number;
  categoryCounts: Record<string, number>;
}

const ANSWER_LABELS = ["A", "B", "C", "D"] as const;

const DIFF_CONFIG: Record<number, { label: string; dot: string; text: string }> = {
  1: { label: "Foundational", dot: "bg-emerald-400", text: "text-emerald-700" },
  2: { label: "Intermediate", dot: "bg-sky-400", text: "text-sky-700" },
  3: { label: "Advanced", dot: "bg-orange-400", text: "text-orange-700" },
  4: { label: "Expert", dot: "bg-red-400", text: "text-red-700" },
};

const ALL_CATEGORIES = new Set<RhythmCategory>([
  "sinus", "atrial", "supraventricular", "av_block", "bundle_branch",
  "junctional", "ventricular", "stemi", "nstemi", "pe_strain", "channelopathy", "pacemaker",
]);

const PROGRESS_WIDTH_CLASSES = [
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

function progressWidthClass(accuracy: number | null): (typeof PROGRESS_WIDTH_CLASSES)[number] {
  const clamped = Math.max(0, Math.min(100, accuracy ?? 0));
  const step = Math.round(clamped / 5);
  return PROGRESS_WIDTH_CLASSES[step] ?? "w-0";
}

export default function QuizMode({ initialCaseId }: QuizModeProps) {
  const [state, setState] = useState<QuizState>("question");
  const [sessionStarted, setSessionStarted] = useState(false);
  const [diagnosisScope, setDiagnosisScope] = useState<DiagnosisScope>("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [showTwelveLead, setShowTwelveLead] = useState(false);
  const [aiResult, setAiResult]         = useState<AnalysisResult | null>(null);
  const [aiError, setAiError]           = useState<string | null>(null);
  const [stats, setStats]               = useState<SessionStats>({ attempted: 0, correct: 0, byCategory: {} });
  const [mounted, setMounted]           = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<Set<RhythmCategory>>(
    new Set(ALL_CATEGORIES)
  );
  // Prevents the selectedCategories effect from overwriting the queue when
  // the initialCase effect resets the filter.
  const skipNextCategoryEffect = useRef(false);


  useEffect(() => {
    if (skipNextCategoryEffect.current) {
      skipNextCategoryEffect.current = false;
      return;
    }
    const active = selectedCategories.size === ALL_CATEGORIES.size
      ? cases
      : cases.filter((c) => selectedCategories.has(c.category));
    if (active.length === 0) return;
    setQueue(shuffle(active));
    setIndex(0);
    setState("question");
    setSelected(null);
    setReveal(null);
    setAiResult(null);
    setAiError(null);
    setShowTwelveLead(false);

  // Jump to a specific case when launched from the Academy or Library
  useEffect(() => {
    if (!initialCase) return;
    // Mark the upcoming selectedCategories effect (triggered by setSelectedCategories
    // below) so it does not reshuffle and overwrite this queue.
    skipNextCategoryEffect.current = true;
    setSelectedCategories(new Set(ALL_CATEGORIES));
    setDiagnosisScope("all");
    setSessionStarted(true);
    setState("question");
    setSelected(null);
    setReveal(null);
    setAiResult(null);
    setAiError(null);
    setShowTwelveLead(false);
    }, [selectedCategories, cases]);
    fetchNextQuestion(initialCaseId).catch((err) => {
      setAiError(err instanceof Error ? err.message : "Unable to load requested case");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialCaseId, meta]);

  const currentDifficulty = current?.difficulty ?? 1;
  const diff = DIFF_CONFIG[currentDifficulty];
  const choices = current?.choices ?? [];
  const isCorrect = reveal?.correct ?? false;

  const accuracyPct =
    stats.attempted > 0 ? Math.round((stats.correct / stats.attempted) * 100) : null;
  const isAllSelected = selectedCategories.size === ALL_CATEGORIES.size;

  const handleSelect = async (choice: string) => {
    if (state !== "question" || !current) return;
    setSelected(choice);

    const res = await fetch("/api/quiz/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ opaqueId: current.opaqueId, choice }),
    });
    const data = await res.json();

    if (!data.success) {
      setAiError(data.error ?? "Unable to check answer");
      return;
    }

    const nextReveal: QuizReveal = {
      correct: data.correct,
      correctRhythm: data.correctRhythm,
      keyFeatures: data.keyFeatures,
      teaching: data.teaching,
      rate: data.rate,
      regularity: data.regularity,
    };
    setReveal(nextReveal);
    setState("revealed");

    setStats((prev) => {
      const cat = prev.byCategory[current.category] ?? { attempted: 0, correct: 0 };
      return {
        attempted: prev.attempted + 1,
        correct: prev.correct + (nextReveal.correct ? 1 : 0),
        byCategory: {
          ...prev.byCategory,
          [current.category]: {
            attempted: cat.attempted + 1,
            correct: cat.correct + (nextReveal.correct ? 1 : 0),
          },
        },
      };
    });
  };

  const handleAIAnalysis = async () => {
    if (!current) return;
    setState("analyzing");
    setAiResult(null);
    setAiError(null);
    try {
      const resp = await fetch(current.twelveLeadUrl);
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

  const handleNext = async () => {
    setState("question");
    setSelected(null);
    setReveal(null);
    setAiResult(null);
    setAiError(null);
    setShowTwelveLead(false);
    try {
      await fetchNextQuestion();
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Unable to load next case");
    }
  };

  const handleSkip = async () => {
    setState("question");
    setSelected(null);
    setReveal(null);
    setAiResult(null);
    setAiError(null);
    setShowTwelveLead(false);
    try {
      await fetchNextQuestion();
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Unable to load next case");
    }
  };

  const toggleCategory = useCallback((cat: RhythmCategory) => {
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  const resetToAll = useCallback(() => {
    setSelectedCategories(new Set(ALL_CATEGORIES));
  }, []);

  const handleBegin = useCallback(async () => {
    if (beginDisabled) return;
    setSessionStarted(true);
    setSeenOpaqueIds([]);
    setState("question");
    setSelected(null);
    setReveal(null);
    setAiResult(null);
    setAiError(null);
    setShowTwelveLead(false);
    try {
      await fetchNextQuestion();
    } catch (err) {
      setAiError(err instanceof Error ? err.message : "Unable to start practice");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beginDisabled]);

  if (!mounted || !meta) return null;

  if (!sessionStarted || !current) {
    return (
      <div className="flex flex-col gap-4">
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Diagnosis Set</p>

          <div className="flex items-center gap-2 mb-3">
            <button
              onClick={() => {
                setDiagnosisScope("all");
                setSelectedCategories(new Set(ALL_CATEGORIES));
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                diagnosisScope === "all"
                  ? "academy-pill-active"
                  : "academy-pill"
              }`}
            >
              All diagnoses
            </button>
            <button
              onClick={() => {
                setDiagnosisScope("selected");
                setSelectedCategories(new Set());
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                diagnosisScope === "selected"
                  ? "academy-pill-active"
                  : "academy-pill"
              }`}
            >
              Selected diagnoses
            </button>
          </div>

          {diagnosisScope === "selected" && (
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              {Array.from(ALL_CATEGORIES).map((cat) => {
                const count = categoryCounts[cat] ?? 0;
                const isActive = selectedCategories.has(cat);
                return (
                  <button
                    key={cat}
                    onClick={() => toggleCategory(cat)}
                    className={`shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap border transition-all ${
                      isActive
                        ? "academy-pill-active"
                        : "academy-pill"
                    }`}
                  >
                    {CATEGORY_LABELS[cat]} · {count}
                  </button>
                );
              })}
              <button
                onClick={resetToAll}
                className="shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap academy-pill transition-all"
              >
                Select all
              </button>
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-slate-500">
              <span className="font-semibold text-slate-700">{activeCaseCount}</span> case{activeCaseCount !== 1 ? "s" : ""} available
            </span>
            {noDiagnosisSelected && (
              <span className="text-xs text-slate-500 font-medium">Select at least 1 diagnosis</span>
            )}
            {tooFewCases && <span className="text-xs text-amber-600 font-medium">Need ≥ 4 cases</span>}
          </div>
        </div>

        <button
          onClick={handleBegin}
          disabled={beginDisabled}
          className="w-full rounded-lg bg-slate-900 text-white py-3 text-sm font-semibold
                     hover:bg-slate-700 active:bg-slate-800 transition-colors duration-150
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Begin
        </button>
      </div>
    );
  }

  const showingTwelveLead = showTwelveLead || state === "revealed" || state === "analyzing";

  return (
    <div className="flex flex-col gap-4">
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
                className={`${progressWidthClass(accuracyPct)} h-full rounded-full transition-all duration-500 ${
                  (accuracyPct ?? 0) >= 80 ? "bg-emerald-500" :
                  (accuracyPct ?? 0) >= 60 ? "bg-amber-400" : "bg-red-400"
                }`}
              />
            </div>
            <span className="font-medium">{accuracyPct}%</span>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={resetToAll}
            className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              isAllSelected
                ? "academy-pill-active"
                : "academy-pill"
            }`}
          >
            All · {meta.totalCases}
          </button>
          {Array.from(ALL_CATEGORIES).map((cat) => {
            const count = categoryCounts[cat] ?? 0;
            const isActive = !isAllSelected && selectedCategories.has(cat);
            return (
              <button
                key={cat}
                onClick={() => toggleCategory(cat)}
                className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? "academy-pill-active"
                    : "academy-pill"
                }`}
              >
                {CATEGORY_LABELS[cat]} · {count}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2 px-0.5">
          <span className="text-xs text-slate-500">
            <span className="font-semibold text-slate-700">{activeCaseCount}</span> case{activeCaseCount !== 1 ? "s" : ""}
          </span>
          {tooFewCases && (
            <span className="flex items-center gap-1 text-xs text-amber-600 font-medium">
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              Need ≥ 4 cases for varied choices
            </span>
          )}
        </div>
      </div>

      <div className="rounded-xl overflow-hidden border border-slate-200 shadow-sm ekg-paper">
        <Image
          key={showingTwelveLead ? current.twelveLeadUrl : current.imageUrl}
          src={showingTwelveLead ? current.twelveLeadUrl : current.imageUrl}
          alt={showingTwelveLead ? "12-lead EKG" : "EKG rhythm strip"}
          width={1600}
          height={900}
          sizes="100vw"
          className="w-full h-auto object-contain"
        />
        <div className="px-3 py-1.5 flex items-center justify-between ekg-paper border-t ekg-paper-border">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-700/60">
            {showingTwelveLead ? "12-Lead EKG" : "Rhythm Strip - Lead II"}
          </span>
          {state === "revealed" && <span className="text-[10px] text-amber-700/50">Teaching view</span>}
        </div>
      </div>

      {state === "question" && !showTwelveLead && (
        <button
          onClick={() => setShowTwelveLead(true)}
          className="flex items-center justify-center gap-2 w-full rounded-lg border border-slate-200
                     bg-white py-2.5 text-sm font-medium text-slate-600
                     hover:border-slate-300 hover:bg-slate-50 hover:text-slate-800
                     transition-all duration-150 shadow-sm group"
        >
          <svg className="w-4 h-4 text-slate-400 group-hover:text-sky-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.8}
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Request 12-lead EKG
        </button>
      )}

      {state === "question" && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-0.5 px-0.5">Identify the rhythm</p>
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
                <span className="w-6 h-6 rounded bg-slate-100 text-slate-500 text-xs font-bold flex items-center justify-center shrink-0">
                  {ANSWER_LABELS[i]}
                </span>
                {choice}
              </button>
            ))}
          </div>
        </div>
      )}

      {state === "question" && (
        <div className="flex justify-center">
          <button
            onClick={handleSkip}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-slate-200
                       bg-white text-slate-500 text-sm
                       hover:border-slate-300 hover:text-slate-600 transition-all duration-150"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
            Skip
          </button>
        </div>
      )}

      {(state === "revealed" || state === "analyzing") && reveal && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {choices.map((choice, i) => {
              const isAnswer = choice === reveal.correctRhythm;
              const isSelected = choice === selected;
              const isDimmed = !isAnswer && !isSelected;

              let containerCls = "flex items-center gap-3 rounded-lg border px-4 py-3.5 text-sm font-medium text-left cursor-default";
              let labelCls = "w-6 h-6 rounded text-xs font-bold flex items-center justify-center shrink-0";

              if (isAnswer) {
                containerCls += " border-emerald-300 bg-emerald-50 text-emerald-800";
                labelCls += " bg-emerald-500 text-white";
              } else if (isSelected) {
                containerCls += " border-red-300 bg-red-50 text-red-800";
                labelCls += " bg-red-500 text-white";
              } else if (isDimmed) {
                containerCls += " border-slate-100 bg-slate-50 text-slate-400 opacity-60";
                labelCls += " bg-slate-200 text-slate-400";
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

          <div
            className={`flex items-start gap-3 rounded-xl border px-4 py-3 ${
              isCorrect ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"
            }`}
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                isCorrect ? "bg-emerald-500" : "bg-red-500"
              }`}
            >
              {isCorrect ? (
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
            <div>
              <p className={`font-semibold text-sm ${isCorrect ? "text-emerald-900" : "text-red-900"}`}>
                {isCorrect ? "Correct" : `Incorrect - this is ${reveal.correctRhythm}`}
              </p>
              {!isCorrect && selected && (
                <p className="text-xs text-red-600 mt-0.5">You selected: {selected}</p>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100 shadow-sm overflow-hidden">
            <div className="px-4 py-3.5">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2.5">Key Features</p>
              <ul className="flex flex-col gap-1.5">
                {reveal.keyFeatures.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-slate-700">
                    <svg className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            <div className="px-4 py-3.5 bg-sky-50">
              <p className="text-[10px] font-bold uppercase tracking-widest text-sky-500 mb-1.5">Teaching Point</p>
              <p className="text-sm text-slate-700 leading-relaxed">{reveal.teaching}</p>
            </div>

            <div className="px-4 py-2.5 flex items-center gap-4 text-xs text-slate-400 bg-slate-50">
              {reveal.rate !== null && reveal.rate > 0 && (
                <span>
                  Rate <span className="font-semibold text-slate-600">{reveal.rate} bpm</span>
                </span>
              )}
              <span>
                Rhythm <span className="font-semibold text-slate-600">{reveal.regularity.replace(/_/g, " ")}</span>
              </span>
            </div>
          </div>

          {!aiResult && !aiError && state !== "analyzing" && (
            <button
              onClick={handleAIAnalysis}
              className="flex items-center justify-center gap-2 w-full rounded-lg border border-slate-200
                         bg-white py-2.5 text-sm font-medium text-slate-600
                         hover:border-sky-200 hover:bg-sky-50 hover:text-sky-700
                         transition-all duration-150 shadow-sm group"
            >
              <svg className="w-4 h-4 text-slate-400 group-hover:text-sky-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.8}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z"
                />
              </svg>
              Get AI 10-step analysis
            </button>
          )}

          {state === "analyzing" && (
            <div className="flex items-center justify-center gap-2.5 py-3 text-sm text-slate-500">
              <svg className="w-4 h-4 animate-spin text-sky-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing...
            </div>
          )}

          {aiError && <p className="text-sm text-red-500 text-center">{aiError}</p>}

          {aiResult && <RhythmReport result={aiResult} />}

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
