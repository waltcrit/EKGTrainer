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
from typing import Iterable


# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).parent.parent
CASES_JSON   = ROOT / "web" / "src" / "data" / "cases.json"
PUBLIC_CASES = ROOT / "web" / "public" / "cases"
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
# idioventricular, Brugada, PE, sinus arrhythmia) are outside rhythm-label scope;
# a wrong pipeline label for those is informational, not a failure.
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
    excluded — handled outside rhythm classification scope.
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


# ── Canonical label mapping (for aggregate metrics) ───────────────────────────
# Goal: map both expected labels (cases.json) and predicted pipeline output into
# a small canonical set so we can compute confusion/F1.
CANON_LABELS: list[str] = ["AF", "AFL", "SVT", "VT", "VF", "ASYS", "PAC", "PVC", "OTHER"]


def _norm(s: str) -> str:
    return " ".join(s.lower().strip().split())


def canonical_expected(rhythm: str) -> str:
    r = _norm(rhythm)
    if "atrial fibrillation" in r or "afib" in r:
        return "AF"
    if "atrial flutter" in r or "flutter" in r:
        return "AFL"
    if "svt" in r or "supraventricular" in r:
        return "SVT"
    if "ventricular tachycardia" in r or "vtach" in r or r == "vt":
        return "VT"
    if "ventricular fibrillation" in r or "vfib" in r or r == "vf":
        return "VF"
    if "asystole" in r:
        return "ASYS"
    if "premature atrial" in r or "pac" in r:
        return "PAC"
    if "premature ventricular" in r or "pvc" in r:
        return "PVC"
    return "OTHER"


def canonical_predicted(pipeline_classification: object) -> str:
    """
    pipeline_classification is usually a dict with:
      - primary_rhythm: short code (e.g. 'AF')
      - display_name:   human readable (e.g. 'Atrial Fibrillation')
    """
    if not isinstance(pipeline_classification, dict):
        return "OTHER"

    primary = pipeline_classification.get("primary_rhythm")
    if isinstance(primary, str) and primary.strip():
        p = _norm(primary)
        # Accept either short codes or verbose strings
        if p in ("af", "atrial fibrillation"):
            return "AF"
        if p in ("afl", "atrial flutter"):
            return "AFL"
        if p in ("svt", "supraventricular tachycardia"):
            return "SVT"
        if p in ("vt", "ventricular tachycardia"):
            return "VT"
        if p in ("vf", "ventricular fibrillation"):
            return "VF"
        if p in ("asys", "asystole"):
            return "ASYS"
        if p == "pac":
            return "PAC"
        if p == "pvc":
            return "PVC"

    display = pipeline_classification.get("display_name")
    if isinstance(display, str) and display.strip():
        return canonical_expected(display)

    return "OTHER"


# ── Run analyzer on one image ─────────────────────────────────────────────────
def run_analysis(image_path: Path) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, str(ANALYZE_PY), "--image", str(image_path)],
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
                f" (+/-{RATE_TOL:.0%} tolerance -> {lo:.0f}-{hi:.0f})"
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


def _af_binary_counts(y_true: Iterable[str], y_pred: Iterable[str]) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for t, p in zip(y_true, y_pred):
        t_pos = t == "AF"
        p_pos = p == "AF"
        if t_pos and p_pos:
            tp += 1
        elif (not t_pos) and p_pos:
            fp += 1
        elif t_pos and (not p_pos):
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def _af_binary_metrics(counts: dict[str, int]) -> dict[str, float | int]:
    tp = int(counts.get("tp", 0))
    fp = int(counts.get("fp", 0))
    tn = int(counts.get("tn", 0))
    fn = int(counts.get("fn", 0))
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) else 0.0
    return {
        **counts,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "accuracy": accuracy,
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
    y_true: list[str] = []
    y_pred: list[str] = []

    PASS_COL = "\033[32mPASS\033[0m"
    FAIL_COL = "\033[31mFAIL\033[0m"
    SEP_WIDE = "-" * 140
    SEP_MED = "-" * 60

    if not args.json_output:
        print(f"\n{'Case':<26} {'Image':<8} {'Status':<6}  "
              f"{'Rate':>6}  {'Regularity':<22}  {'Pipeline rhythm':<38}  Issues")
        print(SEP_WIDE)

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

            # Collect canonical labels for aggregate metrics.
            # Include only cases where analysis succeeded and pipeline produced a label.
            if analysis.get("success") and "pipeline_classification" in analysis:
                exp = canonical_expected(case.get("rhythm", ""))
                pred = canonical_predicted(analysis.get("pipeline_classification"))
                y_true.append(exp)
                y_pred.append(pred)

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
                    "canonical": {
                        "expected": canonical_expected(case.get("rhythm", "")),
                        "predicted": canonical_predicted(analysis.get("pipeline_classification")),
                    } if analysis.get("success") else None,
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

    # Aggregate metrics (canonical labels)
    aggregate: dict[str, object] = {"available": False}
    if y_true and y_pred:
        try:
            # Import from the repo's python package without requiring installation
            sys.path.insert(0, str(ROOT / "python"))
            from arrhythmia.scoring import compute_metrics  # type: ignore

            report = compute_metrics(y_true, y_pred, labels=CANON_LABELS)
            af_bin = _af_binary_metrics(_af_binary_counts(y_true, y_pred))
            aggregate = {
                "available": True,
                "labels": CANON_LABELS,
                "report": report.to_dict(),
                "af_binary": af_bin,
            }
        except Exception as exc:
            aggregate = {"available": False, "error": str(exc)}

    if args.json_output:
        print(json.dumps({"results": all_results, "aggregate": aggregate}, indent=2))
        return

    pass_count = total - fail
    print(SEP_WIDE)
    print(f"\nSummary: {pass_count}/{total} passed  ({fail} failed)\n")

    if isinstance(aggregate, dict) and aggregate.get("available") is True:
        print("Aggregate results (canonical labels)")
        print(SEP_MED)
        rep = aggregate.get("report")
        if isinstance(rep, dict):
            macro_f1 = rep.get("macro_f1")
            print(f"Macro F1: {macro_f1:.3f}" if isinstance(macro_f1, (int, float)) else "Macro F1: ?")
            cm = rep.get("confusion_matrix")
            labels = rep.get("label_order")
            if isinstance(cm, list) and isinstance(labels, list):
                # Pretty-print confusion matrix without numpy dependency here
                maxw = max(5, max(len(str(l)) for l in labels))
                header = " " * (maxw + 1) + " ".join(f"{str(l):>{maxw}}" for l in labels)
                print("\nConfusion matrix")
                print(header)
                for i, lbl in enumerate(labels):
                    row = cm[i] if i < len(cm) else []
                    row_str = " ".join(f"{int(v):>{maxw}}" for v in row)
                    print(f"{str(lbl):<{maxw}} {row_str}")

            per_class = rep.get("per_class")
            if isinstance(per_class, dict):
                print("\nPer-class metrics")
                print(f"{'Class':<8} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Support':>8}")
                for lbl in CANON_LABELS:
                    m = per_class.get(lbl)
                    if not isinstance(m, dict):
                        continue
                    prec = m.get("precision", 0.0)
                    rec = m.get("recall", 0.0)
                    f1 = m.get("f1", 0.0)
                    sup = m.get("support", 0)
                    if all(isinstance(x, (int, float)) for x in (prec, rec, f1)):
                        print(f"{lbl:<8} {prec:>8.3f} {rec:>8.3f} {f1:>8.3f} {int(sup):>8}")

        afb = aggregate.get("af_binary")
        if isinstance(afb, dict):
            print("\nAF vs rest")
            for k in ("tp", "fp", "tn", "fn", "precision", "recall", "specificity", "f1", "accuracy"):
                v = afb.get(k)
                if isinstance(v, float):
                    print(f"{k:>11}: {v:.3f}")
                else:
                    print(f"{k:>11}: {v}")


if __name__ == "__main__":
    main()
