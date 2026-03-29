"use client";

import { useState } from "react";
import type { EKGCase, RhythmCategory } from "@/types/cases";
import { CATEGORY_LABELS, DIFFICULTY_LABELS } from "@/types/cases";

interface CaseLibraryProps {
  cases: EKGCase[];
  onPractice?: (c: EKGCase) => void;
}

const DIFFICULTY_COLORS: Record<number, string> = {
  1: "bg-green-100 text-green-800",
  2: "bg-blue-100 text-blue-800",
  3: "bg-orange-100 text-orange-800",
  4: "bg-red-100 text-red-800",
};

export default function CaseLibrary({ cases, onPractice }: CaseLibraryProps) {
  const [activeCategory, setActiveCategory] = useState<RhythmCategory | "all">("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  const categories = Array.from(
    new Set(cases.map((c) => c.category))
  ) as RhythmCategory[];

  const visible = activeCategory === "all"
    ? cases
    : cases.filter((c) => c.category === activeCategory);

  return (
    <div className="flex flex-col gap-4">
      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setActiveCategory("all")}
          className={`px-3 py-1 rounded-full text-sm font-medium transition-colors
            ${activeCategory === "all"
              ? "bg-gray-800 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
        >
          All ({cases.length})
        </button>
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors
              ${activeCategory === cat
                ? "bg-gray-800 text-white"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
          >
            {CATEGORY_LABELS[cat]} ({cases.filter((c) => c.category === cat).length})
          </button>
        ))}
      </div>

      {/* Case cards */}
      <div className="flex flex-col gap-3">
        {visible.map((c) => (
          <div
            key={c.id}
            className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden"
          >
            {/* Header row */}
            <button
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
              onClick={() => setExpanded(expanded === c.id ? null : c.id)}
            >
              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${DIFFICULTY_COLORS[c.difficulty]}`}>
                  {DIFFICULTY_LABELS[c.difficulty]}
                </span>
                <span className="font-medium text-gray-900 text-sm">{c.rhythm}</span>
              </div>
              <svg
                className={`w-4 h-4 text-gray-400 transition-transform ${expanded === c.id ? "rotate-180" : ""}`}
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {/* Expanded detail */}
            {expanded === c.id && (
              <div className="border-t border-gray-100">
                {/* Strip image */}
                <img
                  src={c.imagePath}
                  alt={c.rhythm}
                  className="w-full object-contain bg-amber-50"
                />

                <div className="p-4 flex flex-col gap-3">
                  {/* Key features */}
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                      Key Features
                    </p>
                    <ul className="flex flex-col gap-1">
                      {c.keyFeatures.map((f, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <span className="text-green-500 mt-0.5 shrink-0">✓</span>
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Teaching point */}
                  <div className="rounded-lg bg-blue-50 border border-blue-100 p-3">
                    <p className="text-xs font-semibold text-blue-600 mb-1">Teaching Point</p>
                    <p className="text-sm text-blue-900 leading-relaxed">{c.teaching}</p>
                  </div>

                  {/* Rate / regularity metadata */}
                  <div className="flex gap-4 text-sm text-gray-500">
                    {c.rate !== null && c.rate > 0 && (
                      <span>Rate: <strong className="text-gray-800">{c.rate} bpm</strong></span>
                    )}
                    <span>Rhythm: <strong className="text-gray-800">{c.regularity.replace(/_/g, " ")}</strong></span>
                  </div>

                  {/* Practice button */}
                  {onPractice && (
                    <button
                      onClick={() => onPractice(c)}
                      className="mt-1 w-full rounded-lg bg-gray-900 text-white py-2 text-sm font-medium hover:bg-gray-700 transition-colors"
                    >
                      Practice this rhythm
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
