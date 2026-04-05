#!/usr/bin/env python3
"""
Pre-compute BioSPPy signal measurements for all training cases.

Reads web/src/data/cases.json, processes each rhythm strip image,
and writes web/src/data/measurements.json.

Usage (run from project root):
    python python/precompute_measurements.py
    python python/precompute_measurements.py --leads 12   # use 12-lead images instead
"""

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import cast

# Allow importing from the same package
sys.path.insert(0, str(Path(__file__).parent))
from analyze_ecg import NumpyEncoder, analyze_signal, build_claude_prompt, digitize_image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--leads", choices=["rhythm", "12"], default="rhythm",
        help="Which image to process: rhythm strip (default) or 12-lead"
    )
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    cases_path = root / "web" / "src" / "data" / "cases.json"
    out_path   = root / "web" / "src" / "data" / "measurements.json"
    public_dir = root / "web" / "public"

    with open(cases_path) as f:
        cases = cast(list[dict[str, str]], json.load(f))

    results: dict[str, dict[str, object]] = {}
    errors: list[dict[str, str]] = []

    for i, case in enumerate(cases):
        case_id = case["id"]
        img_key = "twelveleadPath" if args.leads == "12" else "imagePath"
        # imagePath looks like "/cases/nsr_01.png" — strip leading slash
        rel_path = case[img_key].lstrip("/")
        image_path = str(public_dir / rel_path)

        print(f"[{i+1:2d}/{len(cases)}] {case_id} ({rel_path})", end=" ... ", flush=True)

        try:
            digitized    = digitize_image(image_path)
            measurements = analyze_signal(digitized["signals"], digitized["sampling_rate"])
            prompt       = build_claude_prompt(measurements, digitized["method"])

            results[case_id] = {
                "measurements":      measurements,
                "claude_prompt":     prompt,
                "digitizer_method":  digitized["method"],
                "leads_available":   list(digitized["signals"].keys()),
                "sampling_rate":     digitized["sampling_rate"],
                "image_used":        img_key,
            }
            print(f"OK  HR={measurements['heart_rate_bpm']:.0f}bpm  regularity={measurements['regularity']}")
        except Exception as e:
            print(f"FAIL: {e}")
            errors.append({"case_id": case_id, "error": str(e), "traceback": traceback.format_exc()})

    with open(out_path, "w") as f:
        json.dump(results, f, cls=NumpyEncoder, indent=2)

    print(f"\nWrote {len(results)} entries to {out_path}")
    if errors:
        print(f"\nFailed ({len(errors)}):")
        for err in errors:
            print(f"  {err['case_id']}: {err['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
