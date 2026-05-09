import path from "path";
import fs from "fs";
import matter from "gray-matter";

export type Level = "beginner" | "intermediate" | "advanced";

export interface LessonMeta {
  slug: string;
  level: Level;
  order: number;
  title: string;
}

export interface TOCLevel {
  level: Level;
  label: string;
  lessons: LessonMeta[];
}

export interface TOC {
  levels: TOCLevel[];
}

const LEVEL_LABELS: Record<Level, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

const LEVELS: Level[] = ["beginner", "intermediate", "advanced"];
const BEGINNER_PIN_LAST_SLUG = "15-systematic-approach";

export function getLessonsForLevel(level: Level): LessonMeta[] {
  const dir = path.join(process.cwd(), "content", "learn", level);
  if (!fs.existsSync(dir)) return [];

  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".mdx"));
  const lessons: LessonMeta[] = files.map((file) => {
    const slug = file.replace(/\.mdx$/, "");
    const fullPath = path.join(dir, file);
    const raw = fs.readFileSync(fullPath, "utf-8");
    const { data } = matter(raw);
    return {
      slug,
      level,
      order: data.order ?? 0,
      title: data.title ?? slug,
    };
  });

  return lessons.sort((a, b) => {
    if (level === "beginner") {
      const aPinnedLast = a.slug === BEGINNER_PIN_LAST_SLUG;
      const bPinnedLast = b.slug === BEGINNER_PIN_LAST_SLUG;
      if (aPinnedLast && !bPinnedLast) return 1;
      if (!aPinnedLast && bPinnedLast) return -1;
    }
    return a.order - b.order;
  });
}

export function getTOC(): TOC {
  return {
    levels: LEVELS.map((level) => ({
      level,
      label: LEVEL_LABELS[level],
      lessons: getLessonsForLevel(level),
    })),
  };
}
