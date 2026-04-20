"use client";

import Image from "next/image";
import { useState } from "react";
import type { EKGCase, RhythmCategory } from "@/types/cases";
import { CATEGORY_LABELS, DIFFICULTY_LABELS } from "@/types/cases";
import { getRhythmCriteria } from "@/lib/rhythmCriteria";

interface CaseLibraryProps {
  cases: EKGCase[];
  onPractice?: (c: EKGCase) => void;
  onAnalyze?:  (c: EKGCase) => void;
}

const DIFF_ACCENT: Record<number, { bar: string; badge: string; dot: string }> = {
  1: { bar: "bg-emerald-400", badge: "bg-emerald-100 text-emerald-800", dot: "bg-emerald-400" },
  2: { bar: "bg-teal-400",    badge: "bg-teal-100 text-teal-800",        dot: "bg-teal-400"    },
  3: { bar: "bg-orange-400",  badge: "bg-orange-100 text-orange-800",   dot: "bg-orange-400"  },
  4: { bar: "bg-red-400",     badge: "bg-red-100 text-red-800",         dot: "bg-red-400"     },
};

export default function CaseLibrary({ cases, onPractice, onAnalyze }: CaseLibraryProps) {
  const [activeCategory, setActiveCategory] = useState<RhythmCategory | "all">("all");
  const [expanded, setExpanded]             = useState<string | null>(null);
  const [criteriaOpen, setCriteriaOpen]     = useState<Set<string>>(new Set());

  function toggleCriteria(id: string) {
    setCriteriaOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const categories = Array.from(new Set(cases.map((c) => c.category))) as RhythmCategory[];
  const visible    = activeCategory === "all" ? cases : cases.filter((c) => c.category === activeCategory);

  return (
    <div className="flex flex-col gap-4">

      {/* ── Category filter ───────────────────────────────────────────── */}
      <div className="flex gap-2 overflow-x-auto pb-0.5 scrollbar-none">
        <button
          onClick={() => setActiveCategory("all")}
          className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
            activeCategory === "all"
              ? "academy-pill-active"
              : "academy-pill"
          }`}
        >
          All · {cases.length}
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              activeCategory === cat
                ? "academy-pill-active"
                : "academy-pill"
            }`}
          >
            {CATEGORY_LABELS[cat]} · {cases.filter((c) => c.category === cat).length}
          </button>
        ))}
      </div>

      {/* ── Case list ────────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        {visible.map((c, index) => {
          const acc = DIFF_ACCENT[c.difficulty];
          const isOpen = expanded === c.id;

          return (
            <div key={`${c.id}-${index}`}
              className="academy-panel rounded-xl overflow-hidden
                         transition-shadow hover:shadow-md"
            >
              {/* ── Card header ── */}
              <button
                className="w-full flex items-center gap-3 px-4 py-3.5 text-left"
                onClick={() => {
                  if (isOpen) {
                    setExpanded(null);
                    setCriteriaOpen((prev) => { const next = new Set(prev); next.delete(c.id); return next; });
                  } else {
                    setExpanded(c.id);
                  }
                }}
              >
                {/* Difficulty dot */}
                <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${acc.dot}`} />

                {/* Title */}
                <span className="flex-1 font-medium text-sm text-[var(--academy-ink)] leading-snug">
                  {c.rhythm}
                </span>

                {/* Difficulty badge */}
                <span className={`hidden sm:inline-flex text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${acc.badge}`}>
                  {DIFFICULTY_LABELS[c.difficulty]}
                </span>

                {/* Rate */}
                {c.rate !== null && c.rate > 0 && (
                  <span className="text-xs text-[var(--academy-muted)] shrink-0 hidden md:block">
                    {c.rate} bpm
                  </span>
                )}

                {/* Chevron */}
                <svg
                  className={`w-4 h-4 text-[var(--academy-muted)] shrink-0 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* ── Expanded content ── */}
              {isOpen && (
                <div className="border-t border-[var(--academy-line)]">

                  {/* Difficulty bar accent */}
                  <div className={`h-0.5 w-full ${acc.bar}`} />

                  {/* 12-lead EKG */}
                  <div className="ekg-paper">
                    <Image
                      src={c.twelveleadPath}
                      alt={`${c.rhythm} — 12-lead EKG`}
                      width={1600}
                      height={900}
                      sizes="100vw"
                      className="w-full h-auto object-contain"
                    />
                    <div className="px-3 py-1 border-t ekg-paper-border">
                      <span className="text-[10px] font-semibold uppercase tracking-widest text-amber-700/50">
                        12-Lead EKG
                      </span>
                    </div>
                  </div>

                  <div className="px-4 py-4 flex flex-col gap-4">

                    {/* Key features */}
                    <div>
                      <p className="academy-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--academy-muted)] mb-2">
                        Key Features
                      </p>
                      <ul className="grid sm:grid-cols-2 gap-x-4 gap-y-1.5">
                        {c.keyFeatures.map((f, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-[var(--academy-ink)]">
                            <svg className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                            {f}
                          </li>
                        ))}
                      </ul>
                    </div>

                    {/* Teaching point */}
                    <div className="rounded-lg bg-teal-50/80 border border-teal-100 px-3.5 py-3">
                      <p className="academy-heading text-[10px] font-semibold uppercase tracking-[0.2em] text-teal-700 mb-1.5">
                        Teaching Point
                      </p>
                      <p className="text-sm text-[var(--academy-ink)] leading-relaxed">{c.teaching}</p>
                    </div>

                    {/* AHA/ACC Criteria */}
                    {(() => {
                      const criteria = getRhythmCriteria(c.rhythm);
                      const isOpen = criteriaOpen.has(c.id);
                      if (!criteria) return null;
                      return (
                        <div className="rounded-lg border border-indigo-200 overflow-hidden">
                          <button
                            onClick={() => toggleCriteria(c.id)}
                            className="w-full flex items-center justify-between px-3.5 py-2.5 text-left hover:bg-indigo-50 transition-colors duration-150"
                          >
                            <div className="flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                              <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-600">
                                AHA/ACC Diagnostic Criteria
                              </span>
                            </div>
                            <svg
                              className={`w-4 h-4 text-indigo-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
                              fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </button>
                          {isOpen && (
                            <div className="border-t border-indigo-100 px-3.5 py-3 flex flex-col gap-3">
                              <p className="text-xs text-[var(--academy-ink)] leading-relaxed italic">
                                {criteria.definition}
                              </p>
                              <ul className="flex flex-col gap-1.5">
                                {criteria.diagnosticCriteria.map((item, i) => (
                                  <li key={i} className="flex items-start gap-2.5 text-sm text-[var(--academy-ink)]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0 mt-2" />
                                    {item}
                                  </li>
                                ))}
                              </ul>
                              {criteria.clinicalNotes && (
                                <div className="rounded bg-indigo-50 border border-indigo-100 px-3 py-2">
                                  <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-600 mb-1">
                                    Clinical Notes
                                  </p>
                                  <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
                                    {criteria.clinicalNotes}
                                  </p>
                                </div>
                              )}
                              <p className="text-[10px] text-[var(--academy-muted)]">
                                Source: {criteria.source}
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {/* Meta + practice */}
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div className="flex items-center gap-4 text-xs text-[var(--academy-muted)]">
                        {c.rate !== null && c.rate > 0 && (
                          <span>Rate <strong className="text-[var(--academy-ink)]">{c.rate} bpm</strong></span>
                        )}
                        <span>
                          Rhythm <strong className="text-[var(--academy-ink)]">{c.regularity.replace(/_/g, " ")}</strong>
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {onAnalyze && (
                          <button
                            onClick={() => onAnalyze(c)}
                            className="flex items-center gap-1.5 rounded-lg border border-teal-200
                                       bg-teal-50 text-teal-700 px-4 py-2 text-xs font-semibold
                                       hover:bg-teal-100 transition-colors"
                          >
                            AI Analysis
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.347.347a3.75 3.75 0 01-5.303 0l-.347-.347z" />
                            </svg>
                          </button>
                        )}
                        {onPractice && (
                          <button
                            onClick={() => onPractice(c)}
                            className="flex items-center gap-1.5 rounded-lg bg-[var(--academy-ink)] text-white
                                       px-4 py-2 text-xs font-semibold hover:bg-teal-900 transition-colors"
                          >
                            Practice
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
