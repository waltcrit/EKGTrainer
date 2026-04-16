import Link from "next/link";
import { getTOC } from "@/lib/learn/toc";
import type { Level, LessonMeta } from "@/lib/learn/toc";

const LEVEL_CONFIG: Record<
  Level,
  { label: string; color: string; borderColor: string; icon: string; description: string }
> = {
  beginner: {
    label: "Beginner",
    color: "text-emerald-800",
    borderColor: "border-emerald-200 hover:border-emerald-400",
    icon: "○",
    description:
      "EKG fundamentals: waveforms, intervals, rate calculation, and a 10-step systematic reading method.",
  },
  intermediate: {
    label: "Intermediate",
    color: "text-sky-700",
    borderColor: "border-sky-200 hover:border-sky-400",
    icon: "◆",
    description:
      "Common arrhythmias: sinus rhythms, PACs, PVCs, atrial fibrillation, SVT, and AV blocks.",
  },
  advanced: {
    label: "Advanced",
    color: "text-amber-800",
    borderColor: "border-amber-200 hover:border-amber-400",
    icon: "★",
    description:
      "Life-threatening rhythms, STEMI localization, electrolyte patterns, and challenging edge cases.",
  },
};

export default function LearnIndexPage() {
  const toc = getTOC();

  return (
    <main className="mx-auto max-w-4xl px-4 py-10 sm:py-16">
      {/* Hero */}
      <div className="academy-fade-soft mb-10 text-center">
        <h1 className="academy-heading text-4xl sm:text-5xl font-semibold text-[var(--academy-ink)] mb-3">
          EKG Academy
        </h1>
        <p className="text-base text-[var(--academy-muted)] max-w-xl mx-auto">
          A structured, self-paced curriculum for learning to read EKGs — from first principles to
          advanced patterns.
        </p>
      </div>

      {/* Core principle callout */}
      <div className="academy-fade-up academy-delay-5 academy-panel mb-10 rounded-xl px-5 py-4 flex gap-3 border-teal-200 bg-teal-50/70">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="w-5 h-5 text-teal-600 flex-shrink-0 mt-0.5"
          aria-hidden
        >
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <p className="text-sm text-teal-900">
          <strong>Core principle:</strong> Read every EKG the same way, every time. This curriculum
          teaches a 10-step systematic method and builds your arrhythmia recognition around it.
        </p>
      </div>

      {/* Level cards */}
      <div className="grid gap-5 sm:grid-cols-3">
        {toc.levels.map(({ level, lessons }, index) => {
          const config = LEVEL_CONFIG[level];
          return (
            <Link
              key={level}
              href={`/learn/${level}`}
              className={`academy-fade-up academy-panel group rounded-xl border-2 p-5 shadow-sm transition-all ${
                index === 0 ? "academy-delay-6" : index === 1 ? "academy-delay-7" : "academy-delay-8"
              } ${config.borderColor}`}
            >
              <div className="mb-3 flex items-center gap-2">
                <span className={`text-lg ${config.color}`} aria-hidden>
                  {config.icon}
                </span>
                <h2 className={`text-lg font-bold ${config.color}`}>{config.label}</h2>
              </div>
              <p className="text-sm text-[var(--academy-muted)] mb-4 leading-relaxed">{config.description}</p>
              <div className="text-xs text-[var(--academy-muted)] font-medium">
                {lessons.length} lessons →
              </div>
            </Link>
          );
        })}
      </div>

      {/* Quick-start: first lesson */}
      <div className="mt-10 text-center">
        <p className="text-sm text-[var(--academy-muted)] mb-3">New here? Start from the beginning:</p>
        <Link
          href="/learn/beginner/01-intro"
          className="inline-flex items-center gap-2 rounded-lg bg-[var(--academy-ink)] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-900 transition-colors"
        >
          Start Lesson 1
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="w-4 h-4"
            aria-hidden
          >
            <path
              fillRule="evenodd"
              d="M2 8a.75.75 0 0 1 .75-.75h8.69L8.22 4.03a.75.75 0 0 1 1.06-1.06l4.5 4.5a.75.75 0 0 1 0 1.06l-4.5 4.5a.75.75 0 0 1-1.06-1.06l3.22-3.22H2.75A.75.75 0 0 1 2 8Z"
              clipRule="evenodd"
            />
          </svg>
        </Link>
      </div>
    </main>
  );
}
