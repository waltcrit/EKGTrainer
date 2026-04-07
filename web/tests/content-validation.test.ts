/**
 * Content validation suite for MDX lesson files and supporting .md documents.
 *
 * Covers:
 *  - Frontmatter completeness, types, uniqueness, filename-order alignment
 *  - H1 heading matches frontmatter title; single H1; no skipped heading levels
 *  - Only registered MDX components used; valid prop values
 *  - All stripId references resolve to a real case in cases.json
 *  - Table separator style and column-count consistency
 *  - ptbxl_diagnosis_codes.md table formatting
 */
import { describe, it, expect, beforeAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import matter from "gray-matter";

// ── Path resolution ───────────────────────────────────────────────────────────
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONTENT_DIR = path.resolve(__dirname, "../content/learn");
const CASES_PATH  = path.resolve(__dirname, "../src/data/cases.json");
const PTBXL_MD    = path.resolve(__dirname, "../../scripts/ptbxl_diagnosis_codes.md");

// ── Reference data ────────────────────────────────────────────────────────────
const ALL_CASES: Array<{ id: string }> = JSON.parse(fs.readFileSync(CASES_PATH, "utf8"));
const VALID_CASE_IDS = new Set(ALL_CASES.map((c) => c.id));

// ── Authoritative constants (kept in sync with source files) ─────────────────

// web/src/app/learn/[level]/[slug]/page.tsx → MDX_COMPONENTS
const REGISTERED_COMPONENTS = new Set([
  "DiagramPQRST",
  "LoadStripButton",
  "IdentifyPWave",
  "MeasureInterval",
  "SystematicChecklist",
]);

// web/src/components/learn/DiagramPQRST.tsx → Segment type
const VALID_SEGMENTS = new Set([
  "p", "pr", "qrs", "st", "t", "qt", "baseline", "qrs_notch",
]);

// web/src/components/learn/MeasureInterval.tsx → IntervalType
const VALID_INTERVAL_TYPES = new Set(["PR", "QT"]);

const VALID_LEVELS = ["beginner", "intermediate", "advanced"] as const;
type Level = (typeof VALID_LEVELS)[number];

// ── Data types ────────────────────────────────────────────────────────────────
interface Lesson {
  filePath: string;
  fileName: string; // e.g. "01-intro.mdx"
  level: Level;
  frontmatter: Record<string, unknown>;
  content: string; // body after frontmatter
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function loadAllLessons(): Lesson[] {
  const lessons: Lesson[] = [];
  for (const level of VALID_LEVELS) {
    const dir = path.join(CONTENT_DIR, level);
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".mdx")).sort();
    for (const f of files) {
      const filePath = path.join(dir, f);
      const raw = fs.readFileSync(filePath, "utf8");
      const { data, content } = matter(raw);
      lessons.push({
        filePath,
        fileName: f,
        level,
        frontmatter: data as Record<string, unknown>,
        content,
      });
    }
  }
  return lessons;
}

/** All PascalCase JSX component names used in content. */
function extractComponents(content: string): string[] {
  return [...content.matchAll(/<([A-Z][a-zA-Z0-9]*)/g)].map((m) => m[1]);
}

/** Values for a string prop: propName="value" or propName={'value'}. */
function extractStringProp(content: string, propName: string): string[] {
  const re = new RegExp(`${propName}={?["']([^"'\\s]+)["']}?`, "g");
  return [...content.matchAll(re)].map((m) => m[1]);
}

/** Values inside an array prop: propName={["a", "b"]}. */
function extractArrayProp(content: string, propName: string): string[][] {
  const re = new RegExp(`${propName}=\\{\\[([^\\]]+)\\]\\}`, "g");
  return [...content.matchAll(re)].map((m) =>
    (m[1].match(/["']([^"']+)["']/g) ?? []).map((s) => s.replace(/["']/g, ""))
  );
}

interface Heading {
  level: number;
  text: string;
}

function extractHeadings(content: string): Heading[] {
  return [...content.matchAll(/^(#{1,6})\s+(.+)$/gm)].map((m) => ({
    level: m[1].length,
    text: m[2].trim(),
  }));
}

/** Number of content columns in a table row (| a | b | → 2). */
function countCols(row: string): number {
  return row.split("|").length - 2;
}

/** All table separator lines (only pipes, dashes, spaces). */
function extractSeparators(content: string): string[] {
  return [...content.matchAll(/^\|[\| \-]+\|$/gm)].map((m) => m[0]);
}

// ── Load once ─────────────────────────────────────────────────────────────────
let LESSONS: Lesson[] = [];
beforeAll(() => {
  LESSONS = loadAllLessons();
});

// ─────────────────────────────────────────────────────────────────────────────
// 1. FRONTMATTER
// ─────────────────────────────────────────────────────────────────────────────
describe("Frontmatter", () => {
  it("every lesson has required fields: title, level, order", () => {
    const errors: string[] = [];
    for (const { filePath, frontmatter: fm } of LESSONS) {
      const rel = path.relative(CONTENT_DIR, filePath);
      if (!fm.title)              errors.push(`${rel}: missing 'title'`);
      if (!fm.level)              errors.push(`${rel}: missing 'level'`);
      if (fm.order === undefined) errors.push(`${rel}: missing 'order'`);
    }
    expect(errors).toEqual([]);
  });

  it("level is one of: beginner, intermediate, advanced", () => {
    const errors: string[] = [];
    for (const { filePath, frontmatter: fm } of LESSONS) {
      if (!VALID_LEVELS.includes(fm.level as Level)) {
        errors.push(`${path.relative(CONTENT_DIR, filePath)}: invalid level '${fm.level}'`);
      }
    }
    expect(errors).toEqual([]);
  });

  it("order is a positive integer", () => {
    const errors: string[] = [];
    for (const { filePath, frontmatter: fm } of LESSONS) {
      const o = fm.order;
      if (typeof o !== "number" || !Number.isInteger(o) || o < 1) {
        errors.push(`${path.relative(CONTENT_DIR, filePath)}: invalid order '${o}'`);
      }
    }
    expect(errors).toEqual([]);
  });

  it("order values are unique within each level", () => {
    const errors: string[] = [];
    for (const level of VALID_LEVELS) {
      const seen = new Map<number, string>();
      for (const { fileName, frontmatter: fm } of LESSONS.filter((l) => l.level === level)) {
        const o = fm.order as number;
        if (seen.has(o)) {
          errors.push(`${level}: order ${o} in both '${seen.get(o)}' and '${fileName}'`);
        } else {
          seen.set(o, fileName);
        }
      }
    }
    expect(errors).toEqual([]);
  });

  it("filename numeric prefix matches order field", () => {
    const errors: string[] = [];
    for (const { filePath, fileName, frontmatter: fm } of LESSONS) {
      const match = fileName.match(/^(\d+)-/);
      if (!match) {
        errors.push(`${path.relative(CONTENT_DIR, filePath)}: no numeric prefix in filename`);
        continue;
      }
      const prefix = parseInt(match[1], 10);
      if (prefix !== fm.order) {
        errors.push(
          `${path.relative(CONTENT_DIR, filePath)}: filename prefix ${prefix} ≠ order ${fm.order}`
        );
      }
    }
    expect(errors).toEqual([]);
  });

  it("title is a non-empty string", () => {
    const errors: string[] = [];
    for (const { filePath, frontmatter: fm } of LESSONS) {
      if (typeof fm.title !== "string" || fm.title.trim() === "") {
        errors.push(`${path.relative(CONTENT_DIR, filePath)}: title is empty or not a string`);
      }
    }
    expect(errors).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 2. HEADING STRUCTURE
// ─────────────────────────────────────────────────────────────────────────────
describe("Heading structure", () => {
  it("H1 text matches frontmatter title", () => {
    const errors: string[] = [];
    for (const { filePath, content, frontmatter: fm } of LESSONS) {
      const rel = path.relative(CONTENT_DIR, filePath);
      const h1 = extractHeadings(content).find((h) => h.level === 1);
      if (!h1) {
        errors.push(`${rel}: no H1 found`);
      } else if (h1.text !== fm.title) {
        errors.push(`${rel}: H1 "${h1.text}" ≠ title "${fm.title}"`);
      }
    }
    expect(errors).toEqual([]);
  });

  it("each lesson has exactly one H1", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      const count = extractHeadings(content).filter((h) => h.level === 1).length;
      if (count !== 1) {
        errors.push(`${path.relative(CONTENT_DIR, filePath)}: ${count} H1 headings (expected 1)`);
      }
    }
    expect(errors).toEqual([]);
  });

  it("heading levels never skip (e.g. H1 → H3)", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      const headings = extractHeadings(content);
      for (let i = 1; i < headings.length; i++) {
        if (headings[i].level > headings[i - 1].level + 1) {
          errors.push(
            `${path.relative(CONTENT_DIR, filePath)}: ` +
            `H${headings[i - 1].level} → H${headings[i].level} skips a level ` +
            `("${headings[i].text}")`
          );
        }
      }
    }
    expect(errors).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 3. MDX COMPONENT USAGE
// ─────────────────────────────────────────────────────────────────────────────
describe("MDX components", () => {
  it("all PascalCase JSX components are in MDX_COMPONENTS", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      const unregistered = new Set(
        extractComponents(content).filter((c) => !REGISTERED_COMPONENTS.has(c))
      );
      for (const c of unregistered) {
        errors.push(`${path.relative(CONTENT_DIR, filePath)}: unregistered <${c}>`);
      }
    }
    expect(errors).toEqual([]);
  });

  it("DiagramPQRST highlight values are valid Segment names", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      for (const arr of extractArrayProp(content, "highlight")) {
        for (const seg of arr) {
          if (!VALID_SEGMENTS.has(seg)) {
            errors.push(`${path.relative(CONTENT_DIR, filePath)}: unknown segment "${seg}"`);
          }
        }
      }
    }
    expect(errors).toEqual([]);
  });

  it("all stripId values resolve to a case in cases.json", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      for (const id of extractStringProp(content, "stripId")) {
        if (!VALID_CASE_IDS.has(id)) {
          errors.push(`${path.relative(CONTENT_DIR, filePath)}: unknown stripId "${id}"`);
        }
      }
    }
    expect(errors).toEqual([]);
  });

  it("MeasureInterval intervalType is PR or QT", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      for (const val of extractStringProp(content, "intervalType")) {
        if (!VALID_INTERVAL_TYPES.has(val)) {
          errors.push(`${path.relative(CONTENT_DIR, filePath)}: invalid intervalType "${val}"`);
        }
      }
    }
    expect(errors).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. TABLE FORMATTING  (MDX lessons + ptbxl_diagnosis_codes.md)
// ─────────────────────────────────────────────────────────────────────────────
describe("Table formatting", () => {
  function tableSources(): Array<{ label: string; content: string }> {
    return [
      ...LESSONS.map((l) => ({
        label: path.relative(CONTENT_DIR, l.filePath),
        content: l.content,
      })),
      {
        label: "scripts/ptbxl_diagnosis_codes.md",
        content: fs.readFileSync(PTBXL_MD, "utf8"),
      },
    ];
  }

  it("all table separators use '| --- |' style with spaces", () => {
    const errors: string[] = [];
    for (const { label, content } of tableSources()) {
      for (const sep of extractSeparators(content)) {
        // Detect a column that is only dashes with no surrounding spaces: |---|
        if (/\|---+\|/.test(sep)) {
          errors.push(`${label}: old-style separator: "${sep.trim()}"`);
        }
      }
    }
    expect(errors).toEqual([]);
  });

  it("separator column count matches header row column count", () => {
    const errors: string[] = [];
    for (const { label, content } of tableSources()) {
      const lines = content.split("\n");
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        const isSep = /^\|[\| \-]+\|$/.test(line) && line.includes("---");
        if (!isSep) continue;
        const prev = lines[i - 1].trim();
        if (prev.startsWith("|") && prev.endsWith("|")) {
          const hCols = countCols(prev);
          const sCols = countCols(line);
          if (hCols !== sCols) {
            errors.push(
              `${label} (near "${prev.slice(0, 40)}"): ` +
              `header has ${hCols} cols, separator has ${sCols}`
            );
          }
        }
      }
    }
    expect(errors).toEqual([]);
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 5. COVERAGE CHECKS
// ─────────────────────────────────────────────────────────────────────────────
describe("Curriculum coverage", () => {
  it("beginner lessons are numbered 1–N with no gaps", () => {
    for (const level of VALID_LEVELS) {
      const orders = LESSONS
        .filter((l) => l.level === level)
        .map((l) => l.frontmatter.order as number)
        .sort((a, b) => a - b);
      const expected = Array.from({ length: orders.length }, (_, i) => i + 1);
      expect(orders, `${level}: order sequence has gaps`).toEqual(expected);
    }
  });

  it("lessons with a Practice section have content after it", () => {
    const errors: string[] = [];
    for (const { filePath, content } of LESSONS) {
      const rel = path.relative(CONTENT_DIR, filePath);
      const lines = content.split("\n");
      for (let i = 0; i < lines.length; i++) {
        if (/^##\s+Practice\s*$/.test(lines[i].trim())) {
          // Find the next non-empty line
          const rest = lines.slice(i + 1).join("\n").trim();
          if (rest === "" || rest.startsWith("##")) {
            errors.push(`${rel}: empty Practice section`);
          }
        }
      }
    }
    expect(errors).toEqual([]);
  });
});
