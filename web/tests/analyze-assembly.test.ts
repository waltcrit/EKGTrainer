/**
 * P1 — Stable shape from pure pipeline fixtures (no HTTP).
 */
import { describe, it, expect } from "vitest";
import type { PipelineData } from "@/types/pipeline";
import { assembleAnalysisResult } from "@/lib/analyzeAssembly";

const MINIMAL_PIPELINE: PipelineData = {
  measurements: {
    rr_intervals_ms: [800, 800, 800],
    heart_rate_bpm: 75,
    regularity: "regular",
    p_waves_present: true,
    pr_interval_ms: 160,
    qrs_duration_ms: 90,
    qt_ms: 380,
    qtc_ms: 420,
    qrs_wide: false,
    st: {},
    rhythm_lead: "II",
  },
  digitizer_method: "test-fixture",
  leads_available: ["II"],
  sampling_rate: 250,
  pipeline_classification: {
    primary_rhythm: "NSR",
    display_name: "Normal Sinus Rhythm",
    strip_label: "NSR",
    confidence: 0.85,
    beat_labels: [],
    used_deep_learning: true,
    notes: [],
  },
};

describe("assembleAnalysisResult", () => {
  it("returns all top-level EKGAnalysisResult fields", () => {
    const r = assembleAnalysisResult(MINIMAL_PIPELINE);
    expect(r.rate).toMatchObject({
      bpm: expect.any(Number),
      rr_intervals_ms: expect.any(Array),
      category: expect.stringMatching(/^(bradycardia|normal|tachycardia)$/),
      method: expect.any(String),
      confidence: expect.any(Number),
    });
    expect(r.rhythm.regularity).toMatch(/regular|regularly_irregular|irregularly_irregular/);
    expect(r.p_waves).toMatchObject({ present: expect.any(Boolean), confidence: expect.any(Number) });
    expect(r.pr_interval).toMatchObject({ ms: expect.anything(), confidence: expect.any(Number) });
    expect(r.qrs).toMatchObject({ wide: expect.any(Boolean), confidence: expect.any(Number) });
    expect(r.st_segment).toMatchObject({
      elevation: expect.any(Boolean),
      depression: expect.any(Boolean),
      confidence: expect.any(Number),
    });
    expect(r.t_waves).toMatchObject({ confidence: expect.any(Number) });
    expect(r.qtc).toMatchObject({ prolonged: expect.anything(), confidence: expect.any(Number) });
    expect(typeof r.primary_rhythm).toBe("string");
    expect(typeof r.clinical_impression).toBe("string");
    expect(typeof r.overall_confidence).toBe("number");
    expect(Array.isArray(r.differentials)).toBe(true);
    expect(typeof r.explanation).toBe("string");
    expect(["good", "fair", "poor"]).toContain(r.image_quality);
    expect(r.caveats === null || typeof r.caveats === "string").toBe(true);
    expect(r.pipeline_classification).toBeDefined();
  });

  it("ignores pipeline_classification when it carries error flag", () => {
    const badClass = {
      ...MINIMAL_PIPELINE.pipeline_classification!,
      error: "boom",
    };
    const r = assembleAnalysisResult({
      ...MINIMAL_PIPELINE,
      pipeline_classification: badClass,
    });
    expect(r.pipeline_classification).toEqual(badClass);
    expect(r.primary_rhythm).not.toBe("");
  });
});
