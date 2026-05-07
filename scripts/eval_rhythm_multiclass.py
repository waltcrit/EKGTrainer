#!/usr/bin/env python3
# pyright: basic
"""
Multi-class rhythm evaluation (slice-aware).

This script consumes the machine-readable output from `scripts/validate_analysis.py --json`
and produces:
  - overall confusion + per-class precision/recall/F1
  - slice metrics that are predictive of generalization failures:
      * ectopy-pattern hard negatives for AF (PAC/PVC/bigeminy/trigeminy)
      * terminal rhythms (VF/ASYS)
      * AF-only slice

Usage
-----
  python scripts/validate_analysis.py --skip-12lead --json > validate_results.json
  python scripts/eval_rhythm_multiclass.py --input validate_results.json

Or run validation inline (slower):
  python scripts/eval_rhythm_multiclass.py --run --skip-12lead
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parent.parent


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


CANON_LABELS: list[str] = ["AF", "AFL", "SVT", "VT", "VF", "ASYS", "PAC", "PVC", "OTHER"]


def _load_validate_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError("Input JSON does not look like validate_analysis --json output")
    return data


def _run_validate_inline(skip_12lead: bool) -> dict:
    cmd = [sys.executable, "scripts/validate_analysis.py", "--json"]
    if skip_12lead:
        cmd.append("--skip-12lead")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "validate_analysis.py failed")
    return json.loads(proc.stdout)


def _is_ectopy_hard_negative(case_id: str, expected_rhythm: str) -> bool:
    # Capture explicit ectopy cases + patterned-irregularity cases from the curriculum
    r = _norm(expected_rhythm)
    if any(k in r for k in ("premature atrial", "premature ventricular", "bigeminy", "trigeminy")):
        return True
    if case_id.startswith(("pac_", "pvc_", "bigu_", "trigu_")):
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=str, default="", help="Path to validate_analysis --json output")
    ap.add_argument("--run", action="store_true", help="Run validate_analysis inline instead of reading --input")
    ap.add_argument("--skip-12lead", action="store_true", help="When used with --run, only evaluate strip images")
    args = ap.parse_args()

    if args.run:
        data = _run_validate_inline(skip_12lead=args.skip_12lead)
    else:
        if not args.input:
            raise SystemExit("Provide --input validate_results.json or use --run")
        data = _load_validate_json(Path(args.input))

    results = data.get("results", [])
    if not isinstance(results, list):
        raise SystemExit("validate output missing results[]")

    # Collect canonical labels (prefer validate_analysis' canonical mapping if present)
    y_true: list[str] = []
    y_pred: list[str] = []
    meta: list[dict] = []

    for row in results:
        if not isinstance(row, dict):
            continue
        expected = row.get("expected")
        canon = row.get("canonical")
        if not isinstance(expected, dict):
            continue
        exp_rhythm = expected.get("rhythm", "")
        if not isinstance(exp_rhythm, str):
            continue

        # predicted canonical label
        pred = None
        if isinstance(canon, dict) and isinstance(canon.get("predicted"), str):
            pred = canon.get("predicted")
        if not isinstance(pred, str) or not pred:
            # Fall back to display name if needed
            m = row.get("measurements", {})
            disp = m.get("pipeline") if isinstance(m, dict) else None
            pred = canonical_expected(disp) if isinstance(disp, str) else "OTHER"

        t = canonical_expected(exp_rhythm)
        y_true.append(t)
        y_pred.append(pred)
        meta.append({
            "case_id": row.get("case_id", ""),
            "image": row.get("image", ""),
            "expected_rhythm": exp_rhythm,
        })

    # Score (requires repo python package)
    sys.path.insert(0, str(ROOT / "python"))
    from arrhythmia.scoring import compute_metrics  # type: ignore

    def _score_slice(name: str, idxs: list[int]) -> None:
        if not idxs:
            print(f"\n{name}: (no samples)")
            return
        yt = [y_true[i] for i in idxs]
        yp = [y_pred[i] for i in idxs]
        rep = compute_metrics(yt, yp, labels=CANON_LABELS).to_dict()
        macro_f1 = rep.get("macro_f1")
        print(f"\n{name}: n={len(idxs)}  macro_f1={macro_f1:.3f}" if isinstance(macro_f1, (int, float)) else f"\n{name}: n={len(idxs)}")

        per = rep.get("per_class")
        if isinstance(per, dict):
            # Print the most relevant classes for this project
            for lbl in ("AF", "AFL", "SVT", "VT", "VF", "ASYS", "PAC", "PVC", "OTHER"):
                m = per.get(lbl)
                if not isinstance(m, dict):
                    continue
                sup = int(m.get("support", 0) or 0)
                if sup == 0:
                    continue
                prec = m.get("precision", 0.0)
                rec = m.get("recall", 0.0)
                f1 = m.get("f1", 0.0)
                if all(isinstance(x, (int, float)) for x in (prec, rec, f1)):
                    print(f"  {lbl:<4} sup={sup:<3}  prec={prec:.3f} rec={rec:.3f} f1={f1:.3f}")

    all_idxs = list(range(len(y_true)))
    ectopy_idxs = [
        i
        for i, m in enumerate(meta)
        if _is_ectopy_hard_negative(
            str(m.get("case_id", "")),
            str(m.get("expected_rhythm", "")),
        )
    ]
    af_idxs = [i for i, t in enumerate(y_true) if t == "AF"]
    terminal_idxs = [i for i, t in enumerate(y_true) if t in ("VF", "ASYS")]

    _score_slice("OVERALL", all_idxs)
    _score_slice("AF_only", af_idxs)
    _score_slice("Terminal_only(VF_ASYS)", terminal_idxs)
    _score_slice("Ectopy_hard_negatives", ectopy_idxs)


if __name__ == "__main__":
    main()

