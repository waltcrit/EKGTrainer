import { NextRequest, NextResponse } from "next/server";
import { readQuizImage } from "@/lib/server/casesStore";

interface Params {
  params: Promise<{ opaqueId: string }>;
}

export async function GET(req: NextRequest, { params }: Params) {
  const { opaqueId } = await params;
  const viewParam = req.nextUrl.searchParams.get("view");
  const view = viewParam === "twelvelead" ? "twelvelead" : "strip";

  const file = await readQuizImage(opaqueId, view);
  if (!file) {
    return NextResponse.json({ success: false, error: "Quiz image not found" }, { status: 404 });
  }

  return new NextResponse(file.bytes as unknown as BodyInit, {
    headers: {
      "Content-Type": file.contentType,
      "Cache-Control": "public, max-age=300, s-maxage=300",
    },
  });
}
