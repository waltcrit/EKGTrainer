import { NextRequest, NextResponse } from "next/server";
import { makeQuizQuestion } from "@/lib/server/casesStore";
import type { RhythmCategory } from "@/types/cases";

interface QuizQuestionRequest {
  selectedCategories?: RhythmCategory[];
  excludeOpaqueIds?: string[];
  initialCaseId?: string;
}

export async function POST(req: NextRequest) {
  let body: QuizQuestionRequest = {};
  try {
    body = (await req.json()) as QuizQuestionRequest;
  } catch {
    // Ignore invalid body and use defaults.
  }

  const question = makeQuizQuestion({
    selectedCategories: Array.isArray(body.selectedCategories) ? body.selectedCategories : undefined,
    excludeOpaqueIds: Array.isArray(body.excludeOpaqueIds) ? body.excludeOpaqueIds : undefined,
    initialCaseId: typeof body.initialCaseId === "string" ? body.initialCaseId : undefined,
  });

  if (!question) {
    return NextResponse.json({ success: false, error: "No quiz cases available for selected filters" }, { status: 404 });
  }

  return NextResponse.json({ success: true, question });
}
