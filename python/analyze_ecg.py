#!/usr/bin/env python3
"""
ECG analysis pipeline: image -> digitized signal -> BioSPPy measurements -> JSON stdout.

Usage:
    python analyze_ecg.py --image /tmp/ecg.png

This module re-exports the ecg package for backward compatibility.
Core functionality is in python/ecg/*.
"""

import argparse
import json
import sys
import traceback
from pathlib import Path

from ecg import (
    NumpyEncoder,
    PipelineClassification,
    STResults,
    SignalMeasurements,
    _dumps,
    analyze_signal,
    build_claude_prompt,
    digitize_image,
    run_pipeline_classification,
)

__all__ = [
    "digitize_image",
    "analyze_signal",
    "run_pipeline_classification",
    "build_claude_prompt",
    "NumpyEncoder",
    "_dumps",
    "PipelineClassification",
    "STResults",
    "SignalMeasurements",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="ECG image analysis pipeline")
    parser.add_argument("--image", required=True, help="Path to ECG image file")
    args = parser.parse_args()

    image_path = args.image
    if not Path(image_path).exists():
        print(json.dumps({"error": f"Image not found: {image_path}"}), file=sys.stderr)
        sys.exit(1)

    try:
        digitized = digitize_image(image_path)
        measurements = analyze_signal(
            digitized["signals"],
            digitized["sampling_rate"],
            calibrated=digitized.get("calibrated", False),
        )
        pipeline_classification = run_pipeline_classification(
            digitized["signals"], digitized["sampling_rate"]
        )
        prompt = build_claude_prompt(
            measurements, digitized["method"], pipeline_classification
        )

        result: dict[str, object] = {
            "success": True,
            "measurements": measurements,
            "claude_prompt": prompt,
            "digitizer_method": digitized["method"],
            "leads_available": list(digitized["signals"].keys()),
            "sampling_rate": digitized["sampling_rate"],
            "pipeline_classification": pipeline_classification,
        }
        print(_dumps(result))

    except Exception as e:
        err: dict[str, object] = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        print(_dumps(err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
