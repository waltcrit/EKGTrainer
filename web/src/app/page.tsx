"use client";

import { useState } from "react";
import EKGUploader from "@/components/EKGUploader";
import RhythmReport from "@/components/RhythmReport";
import CaseLibrary from "@/components/CaseLibrary";
import QuizMode from "@/components/QuizMode";
import type { EKGAnalysisResult } from "@/types/analysis";
import type { EKGCase } from "@/types/cases";
import casesData from "@/data/cases.json";

const cases = casesData as EKGCase[];

type Tab = "practice" | "library" | "analyze";
type AnalyzeState = "idle" | "analyzing" | "result" | "error";

// Inline ECG pulse logo mark
function EcgMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round">
      <polyline points="0,12 8,12 11,4 14,20 17,12 21,12 24,7 27,12 30,12 33,16 36,12 48,12" />
    </svg>
  );
}

const TABS: { id: Tab; label: string }[] = [
  { id: "practice", label: "Practice" },
  { id: "library",  label: "Library" },
  { id: "analyze",  label: "Analyze" },
];

export default function Home() {
  const [tab, setTab] = useState<Tab>("practice");
  const [analyzeState, setAnalyzeState] = useState<AnalyzeState>("idle");
  const [result, setResult] = useState<EKGAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePracticeFromLibrary = (c: EKGCase) => {
    void c; // handed off through QuizMode's initial case prop in future
    setTab("practice");
  };

  const handleReset = () => {
    setAnalyzeState("idle");
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Sticky top nav ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2.5 shrink-0">
            <EcgMark className="w-8 h-4 text-sky-600" />
            <span className="font-semibold text-slate-900 text-[15px] tracking-tight select-none">
              EKG Trainer
            </span>
          </div>

          {/* Tab navigation */}
          <nav className="flex items-center gap-0.5">
            {TABS.map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150
                  ${tab === id
                    ? "bg-slate-900 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                  }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-6">

        {tab === "practice" && <QuizMode cases={cases} />}

        {tab === "library" && (
          <CaseLibrary cases={cases} onPractice={handlePracticeFromLibrary} />
        )}

        {tab === "analyze" && (
          <div className="flex flex-col gap-5 max-w-2xl mx-auto">
            {/* Disclaimer */}
            <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
              <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
              <p className="text-sm text-amber-800">
                <span className="font-semibold">Educational use only.</span> Do not upload images
                containing patient information. Not intended for clinical diagnosis.
              </p>
            </div>

            <EKGUploader
              onAnalyzing={() => { setAnalyzeState("analyzing"); setResult(null); setError(null); }}
              onResult={(data) => { setResult(data as EKGAnalysisResult); setAnalyzeState("result"); }}
              onError={(msg) => { setError(msg); setAnalyzeState("error"); }}
              disabled={analyzeState === "analyzing"}
            />

            {analyzeState === "analyzing" && (
              <div className="flex flex-col items-center gap-3 py-12">
                <div className="relative w-10 h-10">
                  <svg className="w-10 h-10 animate-spin text-sky-200" fill="none" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  </svg>
                  <svg className="w-10 h-10 animate-spin text-sky-600 absolute inset-0" fill="none" viewBox="0 0 24 24">
                    <path className="opacity-80" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                </div>
                <p className="text-sm text-slate-500 font-medium">Applying 9-step framework…</p>
              </div>
            )}

            {analyzeState === "error" && error && (
              <div className={`rounded-xl border p-4 flex items-start gap-3 ${
                error.startsWith("Rate limit")
                  ? "border-amber-200 bg-amber-50"
                  : "border-red-200 bg-red-50"
              }`}>
                <svg className={`w-5 h-5 shrink-0 mt-0.5 ${
                  error.startsWith("Rate limit") ? "text-amber-500" : "text-red-500"
                }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <p className={`text-sm font-semibold ${
                    error.startsWith("Rate limit") ? "text-amber-800" : "text-red-800"
                  }`}>
                    {error.startsWith("Rate limit") ? "Rate limit reached" : "Analysis failed"}
                  </p>
                  <p className={`text-sm mt-0.5 ${
                    error.startsWith("Rate limit") ? "text-amber-700" : "text-red-700"
                  }`}>{error}</p>
                  {!error.startsWith("Rate limit") && (
                    <button className="text-sm font-medium text-red-600 hover:text-red-800 mt-2 underline-offset-2 underline"
                      onClick={handleReset}>
                      Try again
                    </button>
                  )}
                </div>
              </div>
            )}

            {analyzeState === "result" && result && (
              <>
                <RhythmReport result={result} />
                <div className="text-center pb-4">
                  <button
                    className="text-sm text-slate-400 hover:text-slate-600 transition-colors underline underline-offset-2"
                    onClick={handleReset}
                  >
                    Analyze another EKG
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200 py-4 mt-8">
        <p className="text-center text-xs text-slate-400">
          For educational use only · Not a substitute for clinical judgment
        </p>
      </footer>
    </div>
  );
}
