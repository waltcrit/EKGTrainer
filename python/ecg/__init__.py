"""ECG analysis package."""
from __future__ import annotations

# Types
from ecg.types import (
    DigitizedResult,
    InferenceResultLike,
    PipelineClassification,
    SignalArray,
    SignalMap,
    SignalMeasurements,
    STLeadResult,
    STResults,
)

# Digitization
from ecg.digitize import (
    _detect_grid_calibration,
    _fallback_digitize,
    digitize_image,
)

# Measurement
from ecg.measure import (
    _clean_r_peaks,
    _detect_j_point,
    _mean_hr,
    _pr_interval,
    _qtc,
    _qrs_width,
    _regularity,
    _rr_intervals,
    _st_analysis,
    analyze_signal,
)

# Pipeline
from ecg.pipeline import run_pipeline_classification

# Prompt
from ecg.prompt import build_claude_prompt

# Utils
from ecg.utils import NumpyEncoder, _dumps

__all__ = [
    # Types
    "DigitizedResult",
    "InferenceResultLike",
    "PipelineClassification",
    "SignalArray",
    "SignalMap",
    "SignalMeasurements",
    "STLeadResult",
    "STResults",
    # Digitization
    "digitize_image",
    "_detect_grid_calibration",
    "_fallback_digitize",
    # Measurement
    "analyze_signal",
    "_rr_intervals",
    "_mean_hr",
    "_clean_r_peaks",
    "_regularity",
    "_detect_j_point",
    "_qrs_width",
    "_pr_interval",
    "_qtc",
    "_st_analysis",
    # Pipeline
    "run_pipeline_classification",
    # Prompt
    "build_claude_prompt",
    # Utils
    "NumpyEncoder",
    "_dumps",
]
