import path from "node:path";
import casesData from "@/data/cases.json";
import type { EKGCase, RhythmCategory } from "@/types/cases";

export interface QuizQuestionPayload {
  opaqueId: string;
  difficulty: 1 | 2 | 3 | 4;
  category: RhythmCategory;
  imageUrl: string;
  twelveLeadUrl: string;
  rate: number | null;
  regularity: EKGCase["regularity"];
  choices: string[];
}

interface CaseWithOpaque {
  opaqueId: string;
  caseData: EKGCase;
}

const allCases = casesData as EKGCase[];

const casesWithOpaque: CaseWithOpaque[] = allCases.map((c, idx) => ({
  opaqueId: `q${(idx + 1).toString(36).padStart(3, "0")}`,
  caseData: c,
}));

const byOpaque = new Map(casesWithOpaque.map((c) => [c.opaqueId, c.caseData]));
const byRealId = new Map(casesWithOpaque.map((c) => [c.caseData.id, c]));

function shuffle<T>(arr: T[]): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

function buildChoices(correct: EKGCase, pool: EKGCase[]): string[] {
  const sameCategory = pool.filter((c) => c.id !== correct.id && c.category === correct.category);
  const other = pool.filter((c) => c.id !== correct.id && c.category !== correct.category);
  const wrongPool = shuffle([...sameCategory, ...other]);
  const wrong = Array.from(new Set(wrongPool.map((c) => c.rhythm)))
    .filter((r) => r !== correct.rhythm)
    .slice(0, 3);
  return shuffle([correct.rhythm, ...wrong]);
}

export function getAllCases(): EKGCase[] {
  return allCases;
}

export function getCaseByOpaqueId(opaqueId: string): EKGCase | null {
  return byOpaque.get(opaqueId) ?? null;
}

export function getOpaqueIdForCaseId(caseId: string): string | null {
  return byRealId.get(caseId)?.opaqueId ?? null;
}

export function getPublicCasesForLibrary(): EKGCase[] {
  return allCases;
}

export function getQuizMeta(): {
  totalCases: number;
  categoryCounts: Record<string, number>;
} {
  const categoryCounts = allCases.reduce<Record<string, number>>((acc, item) => {
    acc[item.category] = (acc[item.category] ?? 0) + 1;
    return acc;
  }, {});

  return {
    totalCases: allCases.length,
    categoryCounts,
  };
}

export function makeQuizQuestion(options: {
  selectedCategories?: RhythmCategory[];
  excludeOpaqueIds?: string[];
  initialCaseId?: string;
}): QuizQuestionPayload | null {
  const selected = new Set(options.selectedCategories ?? []);
  const useAll = selected.size === 0;
  const excluded = new Set(options.excludeOpaqueIds ?? []);

  let candidates = casesWithOpaque.filter((entry) =>
    !excluded.has(entry.opaqueId) && (useAll || selected.has(entry.caseData.category))
  );

  if (options.initialCaseId) {
    const initial = byRealId.get(options.initialCaseId);
    if (initial && (useAll || selected.has(initial.caseData.category))) {
      candidates = [initial, ...candidates.filter((c) => c.opaqueId !== initial.opaqueId)];
    }
  }

  if (candidates.length === 0) return null;

  const selectedCase = options.initialCaseId ? candidates[0] : candidates[Math.floor(Math.random() * candidates.length)];

  const rhythmPool = casesWithOpaque
    .filter((entry) => useAll || selected.has(entry.caseData.category))
    .map((entry) => entry.caseData);

  const choices = buildChoices(selectedCase.caseData, rhythmPool);

  return {
    opaqueId: selectedCase.opaqueId,
    difficulty: selectedCase.caseData.difficulty,
    category: selectedCase.caseData.category,
    imageUrl: `/api/quiz/image/${selectedCase.opaqueId}?view=strip`,
    twelveLeadUrl: `/api/quiz/image/${selectedCase.opaqueId}?view=twelvelead`,
    rate: selectedCase.caseData.rate,
    regularity: selectedCase.caseData.regularity,
    choices,
  };
}

export function checkQuizAnswer(opaqueId: string, choice: string): {
  correct: boolean;
  correctRhythm: string;
  keyFeatures: string[];
  teaching: string;
  rate: number | null;
  regularity: EKGCase["regularity"];
} | null {
  const current = byOpaque.get(opaqueId);
  if (!current) return null;

  return {
    correct: choice === current.rhythm,
    correctRhythm: current.rhythm,
    keyFeatures: current.keyFeatures,
    teaching: current.teaching,
    rate: current.rate,
    regularity: current.regularity,
  };
}

export async function readQuizImage(opaqueId: string, view: "strip" | "twelvelead"): Promise<{
  bytes: Buffer;
  contentType: string;
} | null> {
  const current = byOpaque.get(opaqueId);
  if (!current) return null;

  const relativePath = view === "strip" ? current.imagePath : current.twelveleadPath;
  const filePath = path.join(process.cwd(), "public", relativePath.replace(/^\//, ""));

  const fs = await import("node:fs/promises");
  try {
    const bytes = await fs.readFile(filePath);
    const lower = filePath.toLowerCase();
    const contentType =
      lower.endsWith(".png") ? "image/png" :
      lower.endsWith(".jpg") || lower.endsWith(".jpeg") ? "image/jpeg" :
      lower.endsWith(".gif") ? "image/gif" :
      lower.endsWith(".webp") ? "image/webp" :
      "application/octet-stream";

    return { bytes, contentType };
  } catch {
    return null;
  }
}
