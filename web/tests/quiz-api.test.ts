/**
 * P2 — Quiz routes: opaque IDs, no answer leak on question, 4xx on bad input.
 */
import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { POST as postQuestion } from "@/app/api/quiz/question/route";
import { POST as postAnswer } from "@/app/api/quiz/answer/route";
import type { RhythmCategory } from "@/types/cases";

function postJson(url: string, body: unknown) {
  return new NextRequest(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/quiz/question", () => {
  it("returns opaqueId and choices without leaking answer metadata", async () => {
    const res = await postQuestion(postJson("http://localhost/api/quiz/question", {}));
    expect(res.status).toBe(200);
    const json = (await res.json()) as {
      success: boolean;
      question: Record<string, unknown>;
    };
    expect(json.success).toBe(true);
    const q = json.question;

    expect(typeof q.opaqueId).toBe("string");
    expect(q.opaqueId).toMatch(/^q[0-9a-z]{3}$/);

    const forbidden = [
      "correctRhythm",
      "keyFeatures",
      "teaching",
      "correct",
      "rhythm",
      "id",
      "imagePath",
      "twelveleadPath",
    ];
    for (const key of forbidden) {
      expect(q[key], `question must not include ${key}`).toBeUndefined();
    }

    expect(Array.isArray(q.choices)).toBe(true);
    expect((q.choices as string[]).length).toBeGreaterThanOrEqual(2);
    expect(typeof q.imageUrl).toBe("string");
    expect(String(q.imageUrl)).toContain("/api/quiz/image/");
  });

  it("returns 404 when no cases match filters", async () => {
    const res = await postQuestion(
      postJson("http://localhost/api/quiz/question", {
        selectedCategories: ["nonexistent_category_xyz" as RhythmCategory],
      }),
    );
    expect(res.status).toBe(404);
  });
});

describe("POST /api/quiz/answer", () => {
  it("returns 400 when opaqueId or choice missing", async () => {
    const r1 = await postAnswer(postJson("http://localhost/api/quiz/answer", {}));
    expect(r1.status).toBe(400);

    const r2 = await postAnswer(
      postJson("http://localhost/api/quiz/answer", { opaqueId: "q001" }),
    );
    expect(r2.status).toBe(400);
  });

  it("returns 404 for unknown opaque id", async () => {
    const res = await postAnswer(
      postJson("http://localhost/api/quiz/answer", {
        opaqueId: "qzzz",
        choice: "Normal Sinus Rhythm",
      }),
    );
    expect(res.status).toBe(404);
  });

  it("returns grading payload for a valid opaque id", async () => {
    const qres = await postQuestion(postJson("http://localhost/api/quiz/question", {}));
    const { question } = (await qres.json()) as {
      question: { opaqueId: string; choices: string[] };
    };
    const res = await postAnswer(
      postJson("http://localhost/api/quiz/answer", {
        opaqueId: question.opaqueId,
        choice: question.choices[0],
      }),
    );
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      success: boolean;
      correct: boolean;
      correctRhythm: string;
    };
    expect(body.success).toBe(true);
    expect(typeof body.correct).toBe("boolean");
    expect(typeof body.correctRhythm).toBe("string");
  });
});
