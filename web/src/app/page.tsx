"use client";

import { useState } from "react";
import EKGUploader from "@/components/EKGUploader";
import RhythmReport from "@/components/RhythmReport";
import type { EKGAnalysisResult } from "@/types/analysis";

type AppState = "idle" | "analyzing" | "result" | "error";

export default function Home() {
  const [state, setState] = useState<AppState>("idle");
  const [result, setResult] = useState<EKGAnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyzing = () => {
    setState("analyzing");
    setResult(null);
    setError(null);
  };

  const handleResult = (data: unknown) => {
    setResult(data as EKGAnalysisResult);
    setState("result");
  };

  const handleError = (msg: string) => {
    setError(msg);
    setState("error");
  };

  const handleReset = () => {
    setState("idle");
    setResult(null);
    setError(null);
  };

  return (
    <main className="max-w-3xl mx-auto px-4 py-10 flex flex-col gap-8">
      <header className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">EKG Trainer</h1>
        <p className="text-gray-500 mt-1">
          Upload a photo of an EKG strip or 12-lead ECG for AI-assisted rhythm analysis.
        </p>
      </header>

      <EKGUploader
        onAnalyzing={handleAnalyzing}
        onResult={handleResult}
        onError={handleError}
        disabled={state === "analyzing"}
      />

      {state === "analyzing" && (
        <div className="flex flex-col items-center gap-3 py-8 text-gray-500">
          <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <p className="text-sm">Analyzing EKG — working through 9-step framework...</p>
        </div>
      )}

      {state === "error" && (
        <div className={`rounded-xl border p-4 flex items-start gap-3 ${
          error?.startsWith("Rate limit")
            ? "border-amber-200 bg-amber-50"
            : "border-red-200 bg-red-50"
        }`}>
          <svg className={`w-5 h-5 shrink-0 mt-0.5 ${error?.startsWith("Rate limit") ? "text-amber-500" : "text-red-500"}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className={`text-sm font-medium ${error?.startsWith("Rate limit") ? "text-amber-800" : "text-red-800"}`}>
              {error?.startsWith("Rate limit") ? "Limit reached" : "Analysis failed"}
            </p>
            <p className={`text-sm mt-0.5 ${error?.startsWith("Rate limit") ? "text-amber-700" : "text-red-700"}`}>
              {error}
            </p>
            {!error?.startsWith("Rate limit") && (
              <button className="text-sm text-red-600 underline mt-2" onClick={handleReset}>
                Try again
              </button>
            )}
          </div>
        </div>
      )}

      {state === "result" && result && (
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
    </main>
  );
}
