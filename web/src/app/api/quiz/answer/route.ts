import { NextRequest, NextResponse } from "next/server";
import { checkQuizAnswer } from "@/lib/server/casesStore";

interface QuizAnswerRequest {
  opaqueId?: string;
  choice?: string;
}

export async function POST(req: NextRequest) {
  let body: QuizAnswerRequest = {};
  try {
    body = (await req.json()) as QuizAnswerRequest;
  } catch {
    return NextResponse.json({ success: false, error: "Invalid request body" }, { status: 400 });
  }

  if (typeof body.opaqueId !== "string" || typeof body.choice !== "string") {
    return NextResponse.json({ success: false, error: "opaqueId and choice are required" }, { status: 400 });
  }

  const result = checkQuizAnswer(body.opaqueId, body.choice);
  if (!result) {
    return NextResponse.json({ success: false, error: "Unknown quiz case" }, { status: 404 });
  }

  return NextResponse.json({ success: true, ...result });
}
