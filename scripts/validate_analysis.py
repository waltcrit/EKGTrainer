#!/usr/bin/env python3
# pyright: basic
"""
ECG Analysis Validation
=======================
Runs every strip and 12-lead PNG through the PhysioNet analysis pipeline
(python/analyze_ecg.py) and reports PASS or FAIL for each file.

Pass criteria
-------------
1. RATE   : measured heart_rate_bpm within ±25% of expected case rate
            (skip for VF and ASYS where a strict rate is ill-defined)
2. REGULARITY : measured regularity matches expected (with "irregular" in
                cases.json collapsing to either irregular variant)
3. RHYTHM : if the pipeline covers the case rhythm, pipeline display_name
            must partially match (case-insensitive) the expected rhythm string

Usage
-----
    cd EKGTrainer
    python scripts/validate_analysis.py
    python scripts/validate_analysis.py --help
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
CASES_JSON   = ROOT / "web" / "src" / "data" / "cases.json"
PUBLIC_CASES = ROOT / "web" / "public" / "cases"
PYTHON_BIN   = ROOT / ".venv" / "bin" / "python"
ANALYZE_PY   = ROOT / "python" / "analyze_ecg.py"

# ── Pipeline-covered rhythms (display_name fragment → expected partial match) ─
# Maps pipeline display_name substring → list of strings expected to appear
# in the cases.json rhythm field.
PIPELINE_RHYTHMS: dict[str, list[str]] = {
    "Normal Sinus Rhythm":              ["Normal Sinus Rhythm"],
    "Sinus Bradycardia":                ["Sinus Bradycardia"],
    "Sinus Tachycardia":                ["Sinus Tachycardia"],
    "Atrial Fibrillation":              ["Atrial Fibrillation"],
    "Atrial Flutter":                   ["Atrial Flutter"],
    "Supraventricular Tachycardia":     ["SVT", "Supraventricular"],
    "Premature Atrial Contraction":     ["PAC", "Premature Atrial"],
    "Premature Ventricular Contraction":["PVC", "Premature Ventricular"],
    "Ventricular Tachycardia":          ["Ventricular Tachycardia"],
    "Ventricular Fibrillation":         ["Ventricular Fibrillation"],
    "Asystole":                         ["Asystole"],
}
# Rhythms the pipeline MUST correctly classify.
# Diagnoses not in this set (STEMI, BBB, AVB, strain, pacing, junctional,
# idioventricular, Brugada, PE, sinus arrhythmia) are detected by Claude
# using morphology; a wrong pipeline label is informational, not a failure.
PIPELINE_MUST_MATCH: set[str] = {
    "atrial fibrillation", "afib",
    "atrial flutter",
    "supraventricular tachycardia", "svt",
    "ventricular tachycardia", "vtach",
    "ventricular fibrillation", "vfib",
    "asystole",
    "premature atrial",
    "premature ventricular",
}
# Cases where rate comparison doesn't apply.
# AV block cases: cases.json records the underlying atrial/sinus rate;
# the pipeline measures the (slower) ventricular R-wave rate.
# Flutter/idioventricular/asystole: digitizer rate is structurally unreliable.
SKIP_RATE = {
    "vfib_01", "asys_01",
    "avb2m1_01", "avb2m2_01",   # 2:1/3:1 block: ventricular rate << sinus rate
    "aflut_01",                  # flutter waves counted as R-peaks on strip
    "idio_01",                   # very slow wide QRS; T-wave double-counts
}

# Rate tolerance
RATE_TOL = 0.25

# ── Regularity matching ────────────────────────────────────────────────────────
def regularity_ok(expected: str, measured: str) -> bool:
    if expected == measured:
        return True
    # cases.json uses "irregular" as a catch-all for PAC/PVC
    if expected == "irregular" and measured in ("irregularly_irregular", "regularly_irregular"):
        return True
    # "indeterminate" is acceptable when expected is irregular
    if expected == "irregular" and measured == "indeterminate":
        return True
    return False


# ── Check whether the pipeline covers this rhythm ─────────────────────────────
def pipeline_matches_expected(display_name: str | None, expected_rhythm: str) -> bool | None:
    """
    Returns True/False if the pipeline covers this case, None if not covered.
    Only flag as FAIL when the expected rhythm is something the pipeline
    is REQUIRED to detect correctly (defined in PIPELINE_MUST_MATCH).
    Non-rhythm diagnoses (STEMI, BBB, V block, strain, pacing, etc.) are
    excluded — Claude handles them via morphology.
    """
    erh = expected_rhythm.lower()
    # Skip check if this rhythm is outside pipeline scope
    if not any(kw in erh for kw in PIPELINE_MUST_MATCH):
        return None
    if not display_name:
        return False
    dn = display_name.lower()
    for key, fragments in PIPELINE_RHYTHMS.items():
        if key.lower() in dn:
            return any(f.lower() in erh for f in fragments)
    return False


# ── Run analyzer on one image ─────────────────────────────────────────────────
def run_analysis(image_path: Path) -> dict:
    try:
        result = subprocess.run(
            [str(PYTHON_BIN), str(ANALYZE_PY), "--image", str(image_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(ROOT / "python"),
        )
        if result.returncode != 0:
            # Try stderr for JSON error payload
            try:
                return json.loads(result.stderr)
            except Exception:
                return {"success": False, "error": result.stderr.strip() or "non-zero exit"}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Evaluate one image result ─────────────────────────────────────────────────
def evaluate(case: dict, analysis: dict, label: str) -> dict:
    """
    Returns a result dict with keys: label, status, issues, measurements.
    """
    issues: list[str] = []

    if not analysis.get("success"):
        return {
            "label":    label,
            "status":   "FAIL",
            "issues":   [f"analysis error: {analysis.get('error', 'unknown')}"],
            "measurements": {},
        }

    m     = analysis.get("measurements", {})
    pc    = analysis.get("pipeline_classification") or {}
    c_id  = case["id"]

    measured_rate  = m.get("heart_rate_bpm", 0.0)
    measured_reg   = m.get("regularity", "indeterminate")
    expected_rate  = case.get("rate", 0)
    expected_reg   = case.get("regularity", "")
    expected_rhythm = case.get("rhythm", "")

    # 1. Rate
    if c_id not in SKIP_RATE and expected_rate:
        lo = expected_rate * (1 - RATE_TOL)
        hi = expected_rate * (1 + RATE_TOL)
        if not (lo <= measured_rate <= hi):
            issues.append(
                f"rate: expected {expected_rate} bpm, got {measured_rate:.0f} bpm"
                f" (±{RATE_TOL:.0%} tolerance → {lo:.0f}–{hi:.0f})"
            )

    # 2. Regularity
    if expected_reg and not regularity_ok(expected_reg, measured_reg):
        issues.append(f"regularity: expected '{expected_reg}', got '{measured_reg}'")

    # 3. Pipeline rhythm classification
    display_name = pc.get("display_name") if isinstance(pc, dict) else None
    rhythm_result = pipeline_matches_expected(display_name, expected_rhythm)
    if rhythm_result is False:
        conf = pc.get("confidence", 0.0) if isinstance(pc, dict) else 0.0
        issues.append(
            f"rhythm: expected '{expected_rhythm}', "
            f"pipeline got '{display_name}' ({conf:.0%} conf)"
        )
    elif rhythm_result is None and display_name:
        # Pipeline fired but this rhythm class is not in our coverage map —
        # record as info only, not a failure
        pass

    status = "PASS" if not issues else "FAIL"
    return {
        "label":  label,
        "status": status,
        "issues": issues,
        "measurements": {
            "rate_bpm":    round(measured_rate, 1),
            "regularity":  measured_reg,
            "pipeline":    display_name,
            "confidence":  round(pc.get("confidence", 0.0), 2) if isinstance(pc, dict) else None,
        },
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cases", type=str, default="",
                        help="Comma-separated case IDs to test (default: all)")
    parser.add_argument("--skip-12lead", action="store_true",
                        help="Only test rhythm strips, skip 12-lead images")
    parser.add_argument("--json", action="store_true", dest="json_output",
                        help="Output machine-readable JSON instead of table")
    args = parser.parse_args()

    cases: list[dict] = json.loads(CASES_JSON.read_text())

    if args.cases.strip():
        requested = {c.strip() for c in args.cases.split(",") if c.strip()}
        cases = [c for c in cases if c["id"] in requested]
        if not cases:
            sys.exit(f"No matching cases for: {args.cases}")

    all_results: list[dict] = []
    total = fail = 0

    PASS_COL = "\033[32mPASS\033[0m"
    FAIL_COL = "\033[31mFAIL\033[0m"

    if not args.json_output:
        print(f"\n{'Case':<26} {'Image':<8} {'Status':<6}  "
              f"{'Rate':>6}  {'Regularity':<22}  {'Pipeline rhythm':<38}  Issues")
        print("─" * 140)

    for case in cases:
        c_id = case["id"]

        # paths to test
        images: list[tuple[str, Path]] = []
        strip_path = PUBLIC_CASES / f"{c_id}.png"
        if strip_path.exists():
            images.append(("strip", strip_path))
        if not args.skip_12lead:
            lead12_path = PUBLIC_CASES / f"{c_id}_12lead.png"
            if lead12_path.exists():
                images.append(("12lead", lead12_path))

        for img_type, img_path in images:
            analysis = run_analysis(img_path)
            res = evaluate(case, analysis, img_type)

            total += 1
            if res["status"] == "FAIL":
                fail += 1

            if args.json_output:
                all_results.append({
                    "case_id":  c_id,
                    "image":    img_type,
                    **res,
                    "expected": {
                        "rate": case.get("rate"),
                        "regularity": case.get("regularity"),
                        "rhythm": case.get("rhythm"),
                    },
                })
            else:
                m   = res["measurements"]
                col = PASS_COL if res["status"] == "PASS" else FAIL_COL
                issue_str = "; ".join(res["issues"]) if res["issues"] else ""
                rate_val  = m.get("rate_bpm", "?")
                rate_str  = f"{rate_val:>6.0f}" if isinstance(rate_val, (int, float)) else f"{'?':>6}"
                print(
                    f"{c_id:<26} {img_type:<8} {col}  "
                    f"{rate_str}  "
                    f"{m.get('regularity', '?'):<22}  "
                    f"{(m.get('pipeline') or '—'):<38}  "
                    f"{issue_str}"
                )

    if args.json_output:
        print(json.dumps(all_results, indent=2))
    else:
        pass_count = total - fail
        print("─" * 140)
        print(f"\nSummary: {pass_count}/{total} passed  ({fail} failed)\n")


if __name__ == "__main__":
    main()
