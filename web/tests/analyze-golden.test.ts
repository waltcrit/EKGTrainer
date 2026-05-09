/**
 * P4 — Golden JSON for a fixed precomputed case (update snapshot only when assembly intentionally changes).
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { PipelineData } from "@/types/pipeline";
import { assembleAnalysisResult } from "@/lib/analyzeAssembly";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIXTURE = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "../src/data/measurements.json"),
    "utf8",
  ),
) as Record<string, PipelineData>;

describe("analyze golden — nsr_01", () => {
  it("matches snapshot", () => {
    const data = FIXTURE.nsr_01;
    expect(data).toBeDefined();
    const result = assembleAnalysisResult(data);
    expect(result).toMatchSnapshot();
  });
});
