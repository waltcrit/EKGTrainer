import Link from "next/link";
import { notFound } from "next/navigation";
import { getTOC, getLessonsForLevel } from "@/lib/learn/toc";
import type { Level } from "@/lib/learn/toc";

const VALID_LEVELS: Level[] = ["beginner", "intermediate", "advanced"];

const LEVEL_CONFIG: Record<
  Level,
  { label: string; color: string; accentBg: string; description: string }
> = {
  beginner: {
    label: "Beginner",
    color: "text-emerald-700",
    accentBg: "bg-emerald-50 border-emerald-200",
    description: "EKG fundamentals, waveform anatomy, intervals, and the systematic reading method.",
  },
  intermediate: {
    label: "Intermediate",
    color: "text-sky-700",
    accentBg: "bg-sky-50 border-sky-200",
    description:
      "Common arrhythmias from sinus rhythms through atrial fibrillation, SVT, and AV blocks.",
  },
  advanced: {
    label: "Advanced",
    color: "text-purple-700",
    accentBg: "bg-purple-50 border-purple-200",
    description:
      "Life-threatening rhythms, STEMI localization, electrolyte patterns, and challenging ECG patterns.",
  },
};

interface PageProps {
  params: Promise<{ level: string }>;
}

export async function generateStaticParams() {
  return VALID_LEVELS.map((level) => ({ level }));
}

export default async function LevelPage({ params }: PageProps) {
  const { level } = await params;

  if (!VALID_LEVELS.includes(level as Level)) {
    notFound();
  }

  const typedLevel = level as Level;
  const config = LEVEL_CONFIG[typedLevel];
  const lessons = getLessonsForLevel(typedLevel);
  const toc = getTOC();
  const allLevels = toc.levels;

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:py-12">
      {/* Breadcrumb */}
      <nav className="mb-6 text-xs text-slate-400 flex items-center gap-1.5">
        <Link href="/learn" className="hover:text-slate-700 transition-colors">
          EKG Academy
        </Link>
        <span>/</span>
        <span className={`font-medium ${config.color}`}>{config.label}</span>
      </nav>

      {/* Header */}
      <div className="mb-8">
        <h1 className={`text-2xl sm:text-3xl font-bold tracking-tight ${config.color} mb-2`}>
          {config.label}
        </h1>
        <p className="text-slate-500 text-sm">{config.description}</p>
      </div>

      {/* Lessons list */}
      <div className="space-y-2">
        {lessons.map((lesson, idx) => (
          <Link
            key={lesson.slug}
            href={`/learn/${typedLevel}/${lesson.slug}`}
            className="group flex items-center gap-4 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm hover:border-slate-300 hover:shadow-md transition-all"
          >
            {/* Number badge */}
            <span
              className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${config.accentBg} border`}
            >
              {String(idx + 1).padStart(2, "0")}
            </span>

            {/* Title */}
            <span className="text-sm font-medium text-slate-700 group-hover:text-slate-900 flex-1">
              {lesson.title}
            </span>

            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 16 16"
              fill="currentColor"
              className="w-4 h-4 text-slate-300 group-hover:text-slate-500 flex-shrink-0 transition-colors"
              aria-hidden
            >
              <path
                fillRule="evenodd"
                d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06L7.28 11.78a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z"
                clipRule="evenodd"
              />
            </svg>
          </Link>
        ))}
      </div>

      {/* Other levels */}
      <div className="mt-10 pt-8 border-t border-slate-200">
        <p className="text-xs text-slate-400 uppercase font-semibold tracking-widest mb-4">
          Other levels
        </p>
        <div className="flex gap-3 flex-wrap">
          {allLevels
            .filter((l) => l.level !== typedLevel)
            .map(({ level: lvl, label }) => (
              <Link
                key={lvl}
                href={`/learn/${lvl}`}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 hover:border-slate-300 hover:text-slate-900 transition-all shadow-sm"
              >
                {label} →
              </Link>
            ))}
        </div>
      </div>
    </main>
  );
}
