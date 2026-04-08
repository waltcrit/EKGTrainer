import { NextResponse } from "next/server";
import { getQuizMeta } from "@/lib/server/casesStore";

export async function GET() {
  return NextResponse.json({ success: true, ...getQuizMeta() });
}
