"use client";

import { useState } from "react";
import EKGUploader from "@/components/EKGUploader";
import RhythmReport from "@/components/RhythmReport";
import CaseLibrary from "@/components/CaseLibrary";
import QuizMode from "@/components/QuizMode";
import AboutPage from "@/components/AboutPage";
import type { EKGAnalysisResult } from "@/types/analysis";
import type { EKGCase } from "@/types/cases";
import casesData from "@/data/cases.json";

const cases = casesData as EKGCase[];

type Tab = "practice" | "library" | "analyze" | "about";
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
  { id: "about",    label: "About" },
];

function LandingPage({ onEnter }: { onEnter: (tab: Tab) => void }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 px-6">
      <div className="flex flex-col items-center gap-8 max-w-lg w-full">

        {/* Logo mark */}
        <div className="flex flex-col items-center gap-3">
          <EcgMark className="w-20 h-10 text-sky-600" />
          <div className="text-center">
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">EKG Trainer</h1>
            <p className="text-slate-500 text-sm mt-1">Systematic ECG interpretation · 38 teaching cases</p>
          </div>
        </div>

        {/* Mode cards */}
        <div className="grid grid-cols-1 gap-3 w-full">
          <button
            onClick={() => onEnter("practice")}
            className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white
                       px-5 py-4 text-left shadow-sm hover:border-sky-300 hover:shadow-md
                       transition-all duration-150"
          >
            <div className="w-10 h-10 rounded-lg bg-sky-50 flex items-center justify-center shrink-0
                            group-hover:bg-sky-100 transition-colors">
              <svg className="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-slate-900 text-sm">Practice Mode</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Identify rhythms from strips and 12-leads · A/B/C/D multiple choice
              </p>
            </div>
            <svg className="w-4 h-4 text-slate-300 group-hover:text-sky-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <button
            onClick={() => onEnter("library")}
            className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white
                       px-5 py-4 text-left shadow-sm hover:border-emerald-300 hover:shadow-md
                       transition-all duration-150"
          >
            <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0
                            group-hover:bg-emerald-100 transition-colors">
              <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-slate-900 text-sm">Case Library</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Browse all 38 rhythms · Key features and teaching points
              </p>
            </div>
            <svg className="w-4 h-4 text-slate-300 group-hover:text-emerald-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <button
            onClick={() => onEnter("analyze")}
            className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white
                       px-5 py-4 text-left shadow-sm hover:border-violet-300 hover:shadow-md
                       transition-all duration-150"
          >
            <div className="w-10 h-10 rounded-lg bg-violet-50 flex items-center justify-center shrink-0
                            group-hover:bg-violet-100 transition-colors">
              <svg className="w-5 h-5 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-slate-900 text-sm">AI Analysis</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Upload any EKG · Claude applies the 9-step framework
              </p>
            </div>
            <svg className="w-4 h-4 text-slate-300 group-hover:text-violet-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>

        {/* About + Disclaimer */}
        <div className="flex flex-col items-center gap-2">
          <button
            onClick={() => onEnter("about")}
            className="text-xs text-slate-400 hover:text-slate-600 transition-colors underline underline-offset-2"
          >
            About &amp; Credits
          </button>
          <p className="text-xs text-slate-400 text-center leading-relaxed">
            For educational use only · Not a substitute for clinical judgment
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const [landed, setLanded]   = useState(false);
  const [tab, setTab]         = useState<Tab>("practice");
  const [analyzeState, setAnalyzeState] = useState<AnalyzeState>("idle");
  const [result, setResult]   = useState<EKGAnalysisResult | null>(null);
  const [error, setError]     = useState<string | null>(null);
  const [practiceCase, setPracticeCase]   = useState<EKGCase | null>(null);
  // The image currently being analyzed — shown as a preview in the Analyze tab
  const [analyzePreview, setAnalyzePreview] = useState<string | null>(null);

  // ── Shared analysis runner ────────────────────────────────────────────────
  // All analysis flows converge here: upload, library fast-path, library with image.

  async function runAnalysis(
    imageBase64: string | null,
    mediaType: string | null,
    caseId?: string,
  ) {
    setAnalyzeState("analyzing");
    setResult(null);
    setError(null);

    try {
      const body: Record<string, string> = {};
      if (imageBase64 && mediaType) { body.imageBase64 = imageBase64; body.mediaType = mediaType; }
      if (caseId) body.caseId = caseId;

      const res  = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.success) { setResult(data.result as EKGAnalysisResult); setAnalyzeState("result"); }
      else              { setError(data.error ?? "Analysis failed");    setAnalyzeState("error");  }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
      setAnalyzeState("error");
    }
  }

  // ── Handlers ─────────────────────────────────────────────────────────────

  const handlePracticeFromLibrary = (c: EKGCase) => {
    setPracticeCase(c);
    setTab("practice");
  };

  // Called by EKGUploader when the user selects a file
  const handleFile = (base64: string, mediaType: string) => {
    setAnalyzePreview(`data:${mediaType};base64,${base64}`);
    runAnalysis(base64, mediaType);
  };

  // Called by the "AI Analysis" button in the Case Library
  const handleAnalyzeFromLibrary = async (c: EKGCase) => {
    setTab("analyze");
    setAnalyzePreview(null); // cleared until image is fetched

    try {
      // Fetch the 12-lead image and convert to base64 so Claude has visual context
      const res  = await fetch(c.twelveleadPath);
      const blob = await res.blob();
      const dataUrl = await new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target!.result as string);
        reader.readAsDataURL(blob);
      });
      const base64    = dataUrl.split(",")[1];
      const mediaType = blob.type || "image/png";
      setAnalyzePreview(dataUrl);
      runAnalysis(base64, mediaType, c.id);
    } catch {
      // Image fetch failed — fall back to measurements-only (still works via caseId)
      runAnalysis(null, null, c.id);
    }
  };

  const handleReset = () => {
    setAnalyzeState("idle");
    setResult(null);
    setError(null);
    setAnalyzePreview(null);
  };

  const handleEnter = (dest: Tab) => { setTab(dest); setLanded(true); };

  if (!landed) return <LandingPage onEnter={handleEnter} />;

  return (
    <div className="min-h-screen flex flex-col">
      {/* ── Sticky top nav ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          {/* Logo + Home button */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex items-center gap-2.5">
              <EcgMark className="w-8 h-4 text-sky-600" />
              <span className="font-semibold text-slate-900 text-[15px] tracking-tight select-none">
                EKG Trainer
              </span>
            </div>
            <button
              onClick={() => setLanded(false)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium
                         text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-all duration-150"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Home
            </button>
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

        {tab === "practice" && <QuizMode cases={cases} initialCase={practiceCase} />}

        {tab === "library" && (
          <CaseLibrary
            cases={cases}
            onPractice={handlePracticeFromLibrary}
            onAnalyze={handleAnalyzeFromLibrary}
          />
        )}

        {tab === "about" && <AboutPage />}

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

            {/* Image preview — shown for both library cases and user uploads */}
            {analyzePreview && analyzeState !== "idle" && (
              <div className="bg-[#fff5e6] rounded-xl overflow-hidden border border-[#ffe4b8]">
                <img
                  src={analyzePreview}
                  alt="EKG being analyzed"
                  className="w-full object-contain"
                />
                <div className="px-3 py-1 border-t border-[#ffe4b8]">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-700/50">
                    EKG Image
                  </span>
                </div>
              </div>
            )}

            {/* Uploader — only shown when idle (no active analysis) */}
            {analyzeState === "idle" && (
              <EKGUploader
                onFile={handleFile}
                onError={(msg) => { setError(msg); setAnalyzeState("error"); }}
                disabled={false}
              />
            )}

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
