"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import EKGUploader from "@/components/EKGUploader";
import RhythmReport from "@/components/RhythmReport";
import CaseLibrary from "@/components/CaseLibrary";
import QuizMode from "@/components/QuizMode";
import AboutPage from "@/components/AboutPage";
import SystematicChecklist from "@/components/learn/SystematicChecklist";
import ReturnToAcademy from "@/components/learn/ReturnToAcademy";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import type { EKGAnalysisResult } from "@/types/analysis";
import type { EKGCase } from "@/types/cases";

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

// Backward-compatible IDs used by older lesson content.
const CASE_ID_ALIASES: Record<string, string> = {
  af_01: "afib_01",
  afl_01: "aflut_01",
  avblock_01: "avb1_01",
  bigeminy_01: "pvc_01",
  hyperkalemia_01: "brugada_01",
  ivr_01: "idio_01",
  junctional_01: "junct_01",
  paced_01: "pace_ventricular_01",
  pericarditis_01: "stemi_inf_01",
  sb_01: "brady_01",
  st_01: "tachy_01",
  stemi_anterior_01: "stemi_ant_01",
  tamponade_01: "pe_rv_strain_01",
  vf_01: "vfib_01",
  vt_01: "vtach_01",
};

function resolveCaseId(caseId: string): string {
  return CASE_ID_ALIASES[caseId] ?? caseId;
}

function LandingPage({ onEnter, caseCount }: { onEnter: (tab: Tab) => void; caseCount: number }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="flex flex-col items-center gap-8 max-w-lg w-full">

        {/* Logo mark */}
        <div className="academy-fade-soft flex flex-col items-center gap-3">
          <EcgMark className="w-20 h-10 text-sky-600" />
          <div className="text-center">
            <h1 className="academy-heading text-4xl font-semibold text-[var(--academy-ink)]">EKG Academy</h1>
            <p className="text-[var(--academy-muted)] text-sm mt-1">Systematic ECG interpretation · {caseCount} teaching cases</p>
          </div>
        </div>

        {/* Mode cards */}
        <div className="grid grid-cols-1 gap-3 w-full">
          <button
            onClick={() => onEnter("practice")}
            className="academy-fade-up academy-delay-1 academy-panel group flex items-center gap-4 rounded-xl
                       px-5 py-4 text-left hover:border-sky-300 hover:shadow-md
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
              <p className="font-semibold text-[var(--academy-ink)] text-sm">Practice Mode</p>
              <p className="text-xs text-[var(--academy-muted)] mt-0.5">
                Identify rhythms from strips and 12-leads · A/B/C/D multiple choice
              </p>
            </div>
            <svg className="w-4 h-4 text-[var(--academy-muted)] group-hover:text-sky-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <button
            onClick={() => onEnter("library")}
            className="academy-fade-up academy-delay-2 academy-panel group flex items-center gap-4 rounded-xl
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
              <p className="font-semibold text-[var(--academy-ink)] text-sm">Case Library</p>
              <p className="text-xs text-[var(--academy-muted)] mt-0.5">
                Browse all {caseCount} rhythms · Key features and teaching points
              </p>
            </div>
            <svg className="w-4 h-4 text-[var(--academy-muted)] group-hover:text-emerald-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <button
            onClick={() => onEnter("analyze")}
            className="academy-fade-up academy-delay-3 academy-panel group flex items-center gap-4 rounded-xl
                       px-5 py-4 text-left shadow-sm hover:border-teal-300 hover:shadow-md
                       transition-all duration-150"
          >
            <div className="w-10 h-10 rounded-lg bg-teal-50 flex items-center justify-center shrink-0
                            group-hover:bg-teal-100 transition-colors">
              <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-[var(--academy-ink)] text-sm">Analyze</p>
              <p className="text-xs text-[var(--academy-muted)] mt-0.5">
                Upload any EKG · Signal pipeline applies the systematic interpretation framework
              </p>
            </div>
            <svg className="w-4 h-4 text-[var(--academy-muted)] group-hover:text-teal-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <Link
            href="/learn"
            className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white
                       px-5 py-4 text-left shadow-sm hover:border-sky-300 hover:shadow-md
                       transition-all duration-150"
          >
            <div className="w-10 h-10 rounded-lg bg-sky-50 flex items-center justify-center shrink-0
                            group-hover:bg-sky-100 transition-colors">
              <svg className="w-5 h-5 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-slate-900 text-sm">EKG Academy</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Guided lessons · Master the 17-step systematic checklist
              </p>
            </div>
            <svg className="w-4 h-4 text-slate-300 group-hover:text-sky-400 transition-colors shrink-0"
              fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>

        {/* About + Disclaimer */}
        <div className="flex flex-col items-center gap-2">
          <button
            onClick={() => onEnter("about")}
            className="text-xs text-[var(--academy-muted)] hover:text-[var(--academy-ink)] transition-colors underline underline-offset-2"
          >
            About &amp; Credits
          </button>
          <p className="text-xs text-[var(--academy-muted)] text-center leading-relaxed">
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
  const [practiceCaseId, setPracticeCaseId] = useState<string | null>(null);
  const [libraryCases, setLibraryCases] = useState<EKGCase[] | null>(null);
  const [caseCount, setCaseCount] = useState<number>(0);
  // The image currently being analyzed — shown as a preview in the Analyze tab
  const [analyzePreview, setAnalyzePreview] = useState<string | null>(null);
  // Systematic checklist panel open/closed
  const [checklistOpen, setChecklistOpen] = useState(false);
  // Current strip ID for scoping checklist state
  const [currentStripId, setCurrentStripId] = useState<string | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    async function loadQuizMeta() {
      try {
        const res = await fetch("/api/quiz/meta");
        const data = await res.json();
        if (!cancelled && data.success) {
          setCaseCount(data.totalCases ?? 0);
        }
      } catch {
        if (!cancelled) setCaseCount(0);
      }
    }
    loadQuizMeta();
    return () => {
      cancelled = true;
    };
  }, []);

  // Handle ?caseId=...&tab=... params from LoadStripButton in the Learn module
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const caseId = params.get("caseId");
    const tabParam = params.get("tab") as Tab | null;
    if (caseId) {
      const resolvedCaseId = resolveCaseId(caseId);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPracticeCaseId(resolvedCaseId);
      setCurrentStripId(resolvedCaseId);
      setChecklistOpen(true);
      setLanded(true);
      if (tabParam && ["practice", "library", "analyze", "about"].includes(tabParam)) {
        setTab(tabParam);
      }
      // Clean URL without reloading
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

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
    setPracticeCaseId(c.id);
    setCurrentStripId(c.id);
    setChecklistOpen(true);
    setTab("practice");
  };

  // Called by EKGUploader when the user selects a file
  const handleFile = (base64: string, mediaType: string) => {
    setAnalyzePreview(`data:${mediaType};base64,${base64}`);
    runAnalysis(base64, mediaType);
  };

  // Called by the library “Analyze” action
  const handleAnalyzeFromLibrary = async (c: EKGCase) => {
    setTab("analyze");
    setAnalyzePreview(null); // cleared until image is fetched

    try {
      // Fetch the 12-lead image and digitize via Python when possible (case fast-path still uses measurements.json)
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

  useEffect(() => {
    if (tab !== "library" && tab !== "analyze") return;
    if (libraryCases) return;

    let cancelled = false;
    async function loadLibraryCases() {
      try {
        const res = await fetch("/api/library/cases");
        const data = await res.json();
        if (!cancelled && data.success) {
          setLibraryCases(data.cases as EKGCase[]);
        }
      } catch {
        if (!cancelled) setLibraryCases([]);
      }
    }

    loadLibraryCases();
    return () => {
      cancelled = true;
    };
  }, [tab, libraryCases]);

  if (!landed) return <LandingPage onEnter={handleEnter} caseCount={caseCount} />;

  return (
    <div className="min-h-screen flex flex-col">
      <Header onLogoClick={() => setLanded(false)} />

      {/* Main content */}
      <main className="flex-1">
        {/* Tab Navigation */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-1 border-b border-[var(--academy-line)]">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150
                ${tab === id ? "academy-pill-active" : "academy-pill"}`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Return-to-Academy banner — visible only after navigating from a lesson */}
        <div className="mb-4">
          <ReturnToAcademy />
        </div>

        {tab === "practice" && (
          <div className="space-y-4">
            {/* Systematic checklist toggle */}
            <div>
              <button
                onClick={() => setChecklistOpen((v) => !v)}
                className="academy-panel flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-[var(--academy-muted)] hover:text-[var(--academy-ink)] transition-all"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                  className="w-3.5 h-3.5 text-sky-500"
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M2.75 3.5a.75.75 0 0 0 0 1.5h10.5a.75.75 0 0 0 0-1.5H2.75ZM2 8a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 2 8Zm0 4.25a.75.75 0 0 1 .75-.75h4a.75.75 0 0 1 0 1.5h-4a.75.75 0 0 1-.75-.75Z"
                    clipRule="evenodd"
                  />
                </svg>
                Systematic EKG Read
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 16 16"
                  fill="currentColor"
                  className={`w-3 h-3 text-slate-400 transition-transform ${checklistOpen ? "rotate-180" : ""}`}
                  aria-hidden
                >
                  <path
                    fillRule="evenodd"
                    d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>

              {checklistOpen && (
                <div className="mt-3">
                  <SystematicChecklist stripId={currentStripId} compact />
                </div>
              )}
            </div>

            <QuizMode initialCaseId={practiceCaseId} />
          </div>
        )}

        {tab === "library" && (
          libraryCases ? (
            <CaseLibrary
              cases={libraryCases}
              onPractice={handlePracticeFromLibrary}
              onAnalyze={handleAnalyzeFromLibrary}
            />
          ) : (
            <div className="academy-panel rounded-xl p-6 text-sm text-[var(--academy-muted)]">Loading case library...</div>
          )
        )}

        {tab === "about" && <AboutPage />}

        {tab === "analyze" && (
          <div className="flex flex-col gap-5 max-w-2xl mx-auto">
            {/* Disclaimer */}
            <div className="academy-panel flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50/85 px-4 py-3">
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
              <div className="academy-panel ekg-paper rounded-xl overflow-hidden border ekg-paper-border">
                <Image
                  src={analyzePreview}
                  alt="EKG being analyzed"
                  width={1600}
                  height={900}
                  sizes="100vw"
                  unoptimized
                  className="w-full h-auto object-contain"
                />
                <div className="px-3 py-1 border-t ekg-paper-border">
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
              <div className="academy-panel flex flex-col items-center gap-3 py-12 rounded-xl">
                <div className="relative w-10 h-10">
                  <svg className="w-10 h-10 animate-spin text-sky-200" fill="none" viewBox="0 0 24 24">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                  </svg>
                  <svg className="w-10 h-10 animate-spin text-sky-600 absolute inset-0" fill="none" viewBox="0 0 24 24">
                    <path className="opacity-80" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                </div>
                <p className="text-sm text-[var(--academy-muted)] font-medium">Applying systematic framework…</p>
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

      <Footer />
    </div>
  );
}
