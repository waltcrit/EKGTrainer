/**
 * P0 — Static data contracts: systematic checklist, cases ↔ measurements, public assets.
 */
import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SYSTEMATIC_STEPS, SYSTEMATIC_STEP_IDS } from "@/lib/learn/systematic";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");
const CASES_PATH = path.join(WEB_ROOT, "src/data/cases.json");
const MEASUREMENTS_PATH = path.join(WEB_ROOT, "src/data/measurements.json");
const PUBLIC_DIR = path.join(WEB_ROOT, "public");

interface CaseRow {
  id: string;
  imagePath: string;
  twelveleadPath: string;
}

describe("SYSTEMATIC_STEPS / StepId", () => {
  it("has 17 steps with unique ids aligned to StepId union", () => {
    expect(SYSTEMATIC_STEPS).toHaveLength(17);
    const ids = SYSTEMATIC_STEPS.map((s) => s.id);
    expect(new Set(ids).size).toBe(17);
    expect(SYSTEMATIC_STEP_IDS).toEqual(ids);
  });
});

/** Cases not yet in measurements.json — remove an id here when precompute is added. */
const CASE_IDS_PENDING_PRECOMPUTE = new Set([
  "wpw_01",
  "lngqt_01",
  "hyperkal_01",
  "lae_01",
  "rae_01",
  "lafb_01",
  "bigu_01",
  "trigu_01",
  "qwave_01",
  "pericarditis_01",
  "tamponade_01",
]);

describe("cases.json ↔ measurements.json", () => {
  const cases: CaseRow[] = JSON.parse(fs.readFileSync(CASES_PATH, "utf8"));
  const measurements: Record<string, unknown> = JSON.parse(
    fs.readFileSync(MEASUREMENTS_PATH, "utf8"),
  );

  it("cases without measurements match the pending-precompute allowlist exactly", () => {
    const missing = cases.filter((c) => !(c.id in measurements)).map((c) => c.id);
    const unexpected = missing.filter((id) => !CASE_IDS_PENDING_PRECOMPUTE.has(id));
    expect(unexpected, `add measurements or allowlist: ${unexpected.join(", ")}`).toEqual([]);

    const staleAllowlist = [...CASE_IDS_PENDING_PRECOMPUTE].filter((id) => id in measurements);
    expect(
      staleAllowlist,
      `remove from CASE_IDS_PENDING_PRECOMPUTE: ${staleAllowlist.join(", ")}`,
    ).toEqual([]);

    expect(new Set(missing)).toEqual(CASE_IDS_PENDING_PRECOMPUTE);
  });

  it("every measurements key maps to a known case id (no orphans)", () => {
    const ids = new Set(cases.map((c) => c.id));
    const orphans = Object.keys(measurements).filter((k) => !ids.has(k));
    expect(orphans, `orphan measurement keys: ${orphans.join(", ")}`).toEqual([]);
  });
});

describe("Public case assets", () => {
  const cases: CaseRow[] = JSON.parse(fs.readFileSync(CASES_PATH, "utf8"));

  it("strip and twelve-lead images exist under public/", () => {
    const missing: string[] = [];
    for (const c of cases) {
      for (const rel of [c.imagePath, c.twelveleadPath]) {
        const cleaned = rel.replace(/^\//, "");
        const abs = path.join(PUBLIC_DIR, cleaned);
        if (!fs.existsSync(abs)) missing.push(cleaned);
      }
    }
    expect(missing, `missing files: ${missing.join(", ")}`).toEqual([]);
  });
});
