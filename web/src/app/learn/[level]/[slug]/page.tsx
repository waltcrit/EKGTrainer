import { notFound } from "next/navigation";
import Link from "next/link";
import { MDXRemote } from "next-mdx-remote/rsc";
import { getTOC, getLessonsForLevel } from "@/lib/learn/toc";
import { loadLesson } from "@/lib/learn/lesson-loader";
import type { Level } from "@/lib/learn/toc";
import DiagramPQRST from "@/components/learn/DiagramPQRST";
import LoadStripButton from "@/components/learn/LoadStripButton";
import IdentifyPWave from "@/components/learn/IdentifyPWave";
import MeasureInterval from "@/components/learn/MeasureInterval";
import SystematicChecklist from "@/components/learn/SystematicChecklist";
import { Table, MdxTableOverride } from "@/components/learn/Table";
import { remarkFixCollapsedTables } from "@/lib/mdx/remark-fix-tables";
import QTIntervalDrag from "@/components/learn/QTIntervalDrag";
import PQRSTDiagram from "@/components/learn/PQRSTDiagram";
import ScrollRestorer from "@/components/learn/ScrollRestorer";
import MarkCompleteButton from "./MarkCompleteButton";

const VALID_LEVELS: Level[] = ["beginner", "intermediate", "advanced"];

// MDX component map — all custom components available in lessons.
// `table` (lowercase) overrides the HTML element emitted for every Markdown
// table, routing it through our styled + accessible Table component.
// `Table` (capitalised) allows explicit <Table data={...} /> usage in MDX.
const MDX_COMPONENTS = {
  DiagramPQRST,
  LoadStripButton,
  IdentifyPWave,
  MeasureInterval,
  SystematicChecklist,
  QTIntervalDrag,
  PQRSTDiagram,
  Table,
  table: MdxTableOverride,
};

// Remark plugins for the MDX pipeline (Layer 2 of the collapsed-table fix).
// Layer 1 is the string preprocessor applied in lesson-loader.ts.
const MDX_OPTIONS = {
  mdxOptions: {
    remarkPlugins: [remarkFixCollapsedTables],
  },
} as const;

interface PageProps {
  params: Promise<{ level: string; slug: string }>;
}

export async function generateStaticParams() {
  const paths: { level: string; slug: string }[] = [];
  for (const level of VALID_LEVELS) {
    const lessons = getLessonsForLevel(level);
    for (const lesson of lessons) {
      paths.push({ level, slug: lesson.slug });
    }
  }
  return paths;
}

export default async function LessonPage({ params }: PageProps) {
  const { level, slug } = await params;

  if (!VALID_LEVELS.includes(level as Level)) {
    notFound();
  }

  const typedLevel = level as Level;
  const toc = getTOC();
  const allLessons = toc.levels.flatMap((l) => l.lessons);
  const lesson = loadLesson(typedLevel, slug, allLessons);

  if (!lesson) {
    notFound();
  }

  const { meta, source, prevLesson, nextLesson } = lesson;
  const levelLessons = getLessonsForLevel(typedLevel);

  const LEVEL_COLORS: Record<Level, string> = {
    beginner: "text-emerald-600",
    intermediate: "text-sky-600",
    advanced: "text-purple-600",
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex gap-8">
        {/* Sidebar — lesson nav */}
        <aside className="hidden lg:block w-60 flex-shrink-0">
          <div className="sticky top-20 space-y-1">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3 px-2">
              {typedLevel.charAt(0).toUpperCase() + typedLevel.slice(1)}
            </p>
            {levelLessons.map((l) => {
              const isActive = l.slug === slug;
              return (
                <Link
                  key={l.slug}
                  href={`/learn/${typedLevel}/${l.slug}`}
                  className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
                    isActive
                      ? "bg-sky-50 text-sky-700 font-semibold"
                      : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <span className="font-mono text-xs text-slate-300">
                    {String(l.order).padStart(2, "0")}
                  </span>
                  <span className="truncate">{l.title}</span>
                </Link>
              );
            })}

            {/* Back to levels */}
            <div className="pt-4 border-t border-slate-100 mt-4">
              <Link
                href="/learn"
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-700 transition-colors"
              >
                ← All levels
              </Link>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 min-w-0">
          {/* Restores scroll position when returning from the Trainer */}
          <ScrollRestorer />

          {/* Breadcrumb */}
          <nav className="mb-5 text-xs text-slate-400 flex items-center gap-1.5">
            <Link href="/learn" className="hover:text-slate-700 transition-colors">
              EKG Academy
            </Link>
            <span>/</span>
            <Link
              href={`/learn/${typedLevel}`}
              className={`hover:text-slate-700 transition-colors ${LEVEL_COLORS[typedLevel]}`}
            >
              {typedLevel.charAt(0).toUpperCase() + typedLevel.slice(1)}
            </Link>
            <span>/</span>
            <span className="text-slate-600 font-medium truncate">{meta.title}</span>
          </nav>

          {/* Lesson title */}
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight mb-6">
            {meta.title}
          </h1>

          {/* MDX content */}
          <div className="prose prose-slate max-w-none prose-headings:font-bold prose-headings:text-slate-900 prose-a:text-sky-600 prose-code:text-sky-700 prose-code:bg-sky-50 prose-code:px-1 prose-code:rounded prose-table:text-sm">
            <MDXRemote
              source={source}
              components={MDX_COMPONENTS}
              options={MDX_OPTIONS}
            />
          </div>

          {/* Mark complete + navigation */}
          <div className="mt-10 pt-8 border-t border-slate-200 space-y-5">
            <MarkCompleteButton level={typedLevel} slug={slug} />

            {/* Prev / Next */}
            <div className="flex items-center justify-between gap-4">
              <div>
                {prevLesson && (
                  <Link
                    href={`/learn/${typedLevel}/${prevLesson.slug}`}
                    className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 transition-colors"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 16 16"
                      fill="currentColor"
                      className="w-4 h-4"
                      aria-hidden
                    >
                      <path
                        fillRule="evenodd"
                        d="M9.78 4.22a.75.75 0 0 1 0 1.06L7.06 8l2.72 2.72a.75.75 0 1 1-1.06 1.06L5.47 8.53a.75.75 0 0 1 0-1.06l3.25-3.25a.75.75 0 0 1 1.06 0Z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {prevLesson.title}
                  </Link>
                )}
              </div>
              <div className="text-right">
                {nextLesson && (
                  <Link
                    href={`/learn/${typedLevel}/${nextLesson.slug}`}
                    className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-700 hover:text-slate-900 transition-colors"
                  >
                    {nextLesson.title}
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 16 16"
                      fill="currentColor"
                      className="w-4 h-4"
                      aria-hidden
                    >
                      <path
                        fillRule="evenodd"
                        d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06L7.28 11.78a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </Link>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
