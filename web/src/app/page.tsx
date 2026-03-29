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

type Tab = "analyze" | "practice" | "library";
type AnalyzeState = "idle" | "analyzing" | "result" | "error";

export default function Home() {
  const [tab, setTab] = useState<Tab>("practice");

  // Analyze tab state
  const [analyzeState, setAnalyzeState] = useState<AnalyzeState>("idle");
  const [result, setResult] = useState<EKGAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Library → Practice handoff
  const [practiceCase, setPracticeCase] = useState<EKGCase | null>(null);

  const handlePracticeFromLibrary = (c: EKGCase) => {
    setPracticeCase(c);
    setTab("practice");
  };

  const handleAnalyzing = () => {
    setAnalyzeState("analyzing");
    setResult(null);
    setError(null);
  };
  const handleResult = (data: unknown) => {
    setResult(data as EKGAnalysisResult);
    setAnalyzeState("result");
  };
  const handleError = (msg: string) => {
    setError(msg);
    setAnalyzeState("error");
  };
  const handleReset = () => {
    setAnalyzeState("idle");
    setResult(null);
    setError(null);
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">
      {/* Header */}
      <header className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">EKG Trainer</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Practice rhythm recognition · AI-powered interpretation · For educational use only
        </p>
      </header>

      {/* Tab bar */}
      <nav className="flex rounded-xl bg-gray-100 p-1 gap-1">
        {(["practice", "library", "analyze"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors capitalize
              ${tab === t
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"}`}
          >
            {t === "analyze" ? "Analyze" : t === "practice" ? "Practice" : "Library"}
          </button>
        ))}
      </nav>

      {/* Practice tab */}
      {tab === "practice" && (
        <QuizMode cases={cases} />
      )}

      {/* Library tab */}
      {tab === "library" && (
        <CaseLibrary cases={cases} onPractice={handlePracticeFromLibrary} />
      )}

      {/* Analyze tab */}
      {tab === "analyze" && (
        <div className="flex flex-col gap-5">
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm text-amber-800">
              <strong>Educational use only.</strong> Do not upload images containing patient
              information. This tool is not intended for clinical diagnosis.
            </p>
          </div>

          <EKGUploader
            onAnalyzing={handleAnalyzing}
            onResult={handleResult}
            onError={handleError}
            disabled={analyzeState === "analyzing"}
          />

          {analyzeState === "analyzing" && (
            <div className="flex flex-col items-center gap-3 py-8 text-gray-500">
              <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10"
                  stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <p className="text-sm">Analyzing — working through 9-step framework...</p>
            </div>
          )}

          {analyzeState === "error" && (
            <div className={`rounded-xl border p-4 flex items-start gap-3 ${
              error?.startsWith("Rate limit")
                ? "border-amber-200 bg-amber-50"
                : "border-red-200 bg-red-50"
            }`}>
              <svg className={`w-5 h-5 shrink-0 mt-0.5 ${
                error?.startsWith("Rate limit") ? "text-amber-500" : "text-red-500"
              }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <p className={`text-sm font-medium ${
                  error?.startsWith("Rate limit") ? "text-amber-800" : "text-red-800"
                }`}>
                  {error?.startsWith("Rate limit") ? "Limit reached" : "Analysis failed"}
                </p>
                <p className={`text-sm mt-0.5 ${
                  error?.startsWith("Rate limit") ? "text-amber-700" : "text-red-700"
                }`}>{error}</p>
                {!error?.startsWith("Rate limit") && (
                  <button className="text-sm text-red-600 underline mt-2" onClick={handleReset}>
                    Try again
                  </button>
                )}
              </div>
            </div>
          )}

          {analyzeState === "result" && result && (
            <>
              <RhythmReport result={result} />
              <div className="text-center">
                <button
                  className="text-sm text-gray-500 underline hover:text-gray-700"
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
  );
}
