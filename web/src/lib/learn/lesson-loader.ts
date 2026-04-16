import path from "path";
import fs from "fs";
import matter from "gray-matter";
import type { Level, LessonMeta } from "./toc";
import { fixCollapsedTables } from "@/lib/mdx/remark-fix-tables";

export interface LessonData {
  meta: LessonMeta;
  /** Raw MDX source — pass to next-mdx-remote for rendering */
  source: string;
  prevLesson: LessonMeta | null;
  nextLesson: LessonMeta | null;
}

function normalizeHeadingText(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function stripLeadingTitleHeading(content: string, title: string): string {
  const match = content.match(/^\s*#\s+(.+)\n*/);

  if (!match) {
    return content;
  }

  const headingText = match[1].trim();

  if (normalizeHeadingText(headingText) !== normalizeHeadingText(title)) {
    return content;
  }

  return content.slice(match[0].length).replace(/^\s*\n/, "");
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
  // Expand any collapsed inline tables before handing off to MDXRemote.
  // This is Layer 1 of the two-layer fix; the remark plugin is Layer 2.
  const normalised = fixCollapsedTables(raw);
  const { data, content } = matter(normalised);

  const meta: LessonMeta = {
    slug,
    level,
    order: data.order ?? 0,
    title: data.title ?? slug,
  };
  const source = stripLeadingTitleHeading(content, meta.title);

  // Prev / next within the same level, sorted by order
  const sorted = allLessons
    .filter((l) => l.level === level)
    .sort((a, b) => a.order - b.order);

  const idx = sorted.findIndex((l) => l.slug === slug);
  const prevLesson = idx > 0 ? sorted[idx - 1] : null;
  const nextLesson = idx < sorted.length - 1 ? sorted[idx + 1] : null;

  return { meta, source, prevLesson, nextLesson };
}
