import { NextResponse } from "next/server";
import { getPublicCasesForLibrary } from "@/lib/server/casesStore";

export async function GET() {
  return NextResponse.json({ success: true, cases: getPublicCasesForLibrary() });
}
