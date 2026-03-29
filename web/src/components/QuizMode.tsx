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

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildChoices(correct: EKGCase, all: EKGCase[]): string[] {
  // 3 wrong answers: prefer same category, fall back to random
  const sameCategory = all.filter(
    (c) => c.id !== correct.id && c.category === correct.category
  );
  const other = all.filter(
    (c) => c.id !== correct.id && c.category !== correct.category
  );
  const pool = shuffle([...sameCategory, ...other]);
  const wrong = Array.from(
    new Set(pool.map((c) => c.rhythm))
  )
    .filter((r) => r !== correct.rhythm)
    .slice(0, 3);

  return shuffle([correct.rhythm, ...wrong]);
}

export default function QuizMode({ cases }: QuizModeProps) {
  const [queue, setQueue] = useState<EKGCase[]>(cases);
  const [index, setIndex] = useState(0);
  const [state, setState] = useState<QuizState>("question");
  const [selected, setSelected] = useState<string | null>(null);
  const [aiResult, setAiResult] = useState<AnalysisResult | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [stats, setStats] = useState<SessionStats>({
    attempted: 0, correct: 0, byCategory: {},
  });
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setQueue(shuffle(cases));
    setMounted(true);
  }, [cases]);

  const current = queue[index % queue.length];
  const choices = useMemo(
    () => (mounted ? buildChoices(current, cases) : []),
    [current, cases, mounted]
  );

  const isCorrect = selected === current.rhythm;

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
        byCategory: {
          ...prev.byCategory,
          [current.category]: {
            attempted: cat.attempted + 1,
            correct: cat.correct + (correct ? 1 : 0),
          },
        },
      };
    });
  };

  const handleAIAnalysis = async () => {
    setState("analyzing");
    setAiResult(null);
    setAiError(null);
    try {
      // Fetch the image and convert to base64
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
      if (data.success) {
        setAiResult(data.result);
      } else {
        setAiError(data.error ?? "Analysis failed");
      }
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
  };

  const accuracyPct = stats.attempted > 0
    ? Math.round((stats.correct / stats.attempted) * 100)
    : null;

  if (!mounted) return null;

  return (
    <div className="flex flex-col gap-5">
      {/* Session stats bar */}
      {stats.attempted > 0 && (
        <div className="flex items-center justify-between rounded-xl bg-gray-100 px-4 py-2 text-sm">
          <span className="text-gray-600">
            Session: <strong>{stats.attempted}</strong> attempted
          </span>
          <span className={`font-semibold ${
            (accuracyPct ?? 0) >= 80 ? "text-green-700" :
            (accuracyPct ?? 0) >= 60 ? "text-yellow-700" : "text-red-700"
          }`}>
            {accuracyPct}% accuracy
          </span>
        </div>
      )}

      {/* EKG strip */}
      <div className="rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <img
          src={current.imagePath}
          alt="EKG strip — identify the rhythm"
          className="w-full object-contain bg-amber-50"
        />
      </div>

      {/* Question / choices */}
      {state === "question" && (
        <div className="flex flex-col gap-3">
          <p className="text-sm font-semibold text-gray-700 text-center">
            What rhythm is this?
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {choices.map((choice) => (
              <button
                key={choice}
                onClick={() => handleSelect(choice)}
                className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-left
                           hover:border-gray-400 hover:bg-gray-50 transition-colors"
              >
                {choice}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Revealed state */}
      {(state === "revealed" || state === "analyzing") && (
        <div className="flex flex-col gap-4">
          {/* Result banner */}
          <div className={`rounded-xl p-4 flex items-start gap-3 ${
            isCorrect ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"
          }`}>
            <span className="text-xl">{isCorrect ? "✓" : "✗"}</span>
            <div>
              <p className={`font-semibold ${isCorrect ? "text-green-800" : "text-red-800"}`}>
                {isCorrect ? "Correct!" : `Incorrect — this is ${current.rhythm}`}
              </p>
              {!isCorrect && selected && (
                <p className="text-sm text-red-700 mt-0.5">You answered: {selected}</p>
              )}
            </div>
          </div>

          {/* Key features + teaching point */}
          <div className="rounded-xl border border-gray-200 bg-white p-4 flex flex-col gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Key Features
              </p>
              <ul className="flex flex-col gap-1">
                {current.keyFeatures.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-green-500 mt-0.5 shrink-0">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-lg bg-blue-50 border border-blue-100 p-3">
              <p className="text-xs font-semibold text-blue-600 mb-1">Teaching Point</p>
              <p className="text-sm text-blue-900 leading-relaxed">{current.teaching}</p>
            </div>
          </div>

          {/* AI deep analysis */}
          {!aiResult && !aiError && state !== "analyzing" && (
            <button
              onClick={handleAIAnalysis}
              className="rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium
                         text-gray-700 hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
              </svg>
              Get AI 9-step analysis
            </button>
          )}

          {state === "analyzing" && (
            <div className="flex items-center justify-center gap-2 py-3 text-gray-500 text-sm">
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Analyzing...
            </div>
          )}

          {aiError && (
            <p className="text-sm text-red-600 text-center">{aiError}</p>
          )}

          {aiResult && <RhythmReport result={aiResult} />}

          {/* Next button */}
          <button
            onClick={handleNext}
            className="w-full rounded-lg bg-gray-900 text-white py-2.5 text-sm font-medium
                       hover:bg-gray-700 transition-colors"
          >
            Next case →
          </button>
        </div>
      )}
    </div>
  );
}
