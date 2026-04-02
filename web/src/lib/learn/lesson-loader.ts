import path from "path";
import fs from "fs";
import matter from "gray-matter";
import type { Level, LessonMeta } from "./toc";

export interface LessonData {
  meta: LessonMeta;
  /** Raw MDX source — pass to next-mdx-remote for rendering */
  source: string;
  prevLesson: LessonMeta | null;
  nextLesson: LessonMeta | null;
}

export function loadLesson(
  level: Level,
  slug: string,
  allLessons: LessonMeta[]
): LessonData | null {
  const filePath = path.join(
    process.cwd(),
    "content",
    "learn",
    level,
    `${slug}.mdx`
  );

  if (!fs.existsSync(filePath)) return null;

  const raw = fs.readFileSync(filePath, "utf-8");
  const { data, content } = matter(raw);

  const meta: LessonMeta = {
    slug,
    level,
    order: data.order ?? 0,
    title: data.title ?? slug,
  };

  // Prev / next within the same level, sorted by order
  const sorted = allLessons
    .filter((l) => l.level === level)
    .sort((a, b) => a.order - b.order);

  const idx = sorted.findIndex((l) => l.slug === slug);
  const prevLesson = idx > 0 ? sorted[idx - 1] : null;
  const nextLesson = idx < sorted.length - 1 ? sorted[idx + 1] : null;

  return { meta, source: content, prevLesson, nextLesson };
}
