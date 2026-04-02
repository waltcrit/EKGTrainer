"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { TOC } from "@/lib/learn/toc";

interface Props {
  toc: TOC;
  /** Completed lesson keys in "level/slug" format */
  completed?: string[];
}

const LEVEL_ICONS: Record<string, string> = {
  beginner: "○",
  intermediate: "◆",
  advanced: "★",
};

const LEVEL_COLORS: Record<string, string> = {
  beginner: "text-emerald-600",
  intermediate: "text-sky-600",
  advanced: "text-purple-600",
};

export default function LessonNav({ toc, completed = [] }: Props) {
  const pathname = usePathname();

  return (
    <nav className="space-y-5" aria-label="Lesson navigation">
      {toc.levels.map(({ level, label, lessons }) => (
        <div key={level}>
          {/* Level heading */}
          <div
            className={`flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest mb-2 ${LEVEL_COLORS[level]}`}
          >
            <span aria-hidden>{LEVEL_ICONS[level]}</span>
            {label}
          </div>

          {/* Lesson list */}
          <ol className="space-y-0.5">
            {lessons.map((lesson) => {
              const href = `/learn/${level}/${lesson.slug}`;
              const isActive = pathname === href;
              const isDone = completed.includes(`${level}/${lesson.slug}`);

              return (
                <li key={lesson.slug}>
                  <Link
                    href={href}
                    className={`flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
                      isActive
                        ? "bg-sky-50 text-sky-700 font-semibold"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                    aria-current={isActive ? "page" : undefined}
                  >
                    {/* Completion badge */}
                    <span
                      className={`flex-shrink-0 w-4 h-4 rounded-full border text-xs flex items-center justify-center ${
                        isDone
                          ? "bg-emerald-500 border-emerald-500 text-white"
                          : isActive
                          ? "border-sky-400"
                          : "border-slate-300"
                      }`}
                      aria-label={isDone ? "Complete" : ""}
                    >
                      {isDone && (
                        <svg viewBox="0 0 8 8" fill="none" className="w-2.5 h-2.5" aria-hidden>
                          <path
                            d="M1.5 4l2 2 3-3"
                            stroke="currentColor"
                            strokeWidth={1.5}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </span>

                    {/* Lesson number + title */}
                    <span className="truncate">
                      <span className="text-slate-400 font-mono text-xs mr-1">
                        {String(lesson.order).padStart(2, "0")}
                      </span>
                      {lesson.title}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ol>
        </div>
      ))}
    </nav>
  );
}
