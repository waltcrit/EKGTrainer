"""Arrhythmia classification pipeline (PhysioNet-compatible)."""
from __future__ import annotations

import logging
import os
from typing import cast

import numpy as np

from ecg.types import InferenceResultLike, PipelineClassification, SignalMap

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Arrhythmia pipeline — optional
# ---------------------------------------------------------------------------
try:
    from arrhythmia.inference import classify_ecg
    from arrhythmia.constants import DISPLAY_NAMES as _arr_display_names
    _pipeline_available = True
except ImportError:
    classify_ecg = None
    _arr_display_names: dict[str, str] = {}
    _pipeline_available = False
    logger.debug("Arrhythmia pipeline not available; classification will be skipped")


def run_pipeline_classification(
    signals: SignalMap,
    sampling_rate: int,
    precomputed_rpeaks: list[int] | None = None,
    precomputed_fs: int | None = None,
) -> PipelineClassification | None:
    """
    Run the arrhythmia pipeline on Lead II signal.
    Accepts precomputed_rpeaks to skip redundant detection.
    """
    if not _pipeline_available:
        return None
    assert classify_ecg is not None

    lead = "II" if "II" in signals else next(iter(signals))
    signal = np.asarray(signals[lead], dtype=np.float64)

    def _label_to_str(value: object) -> str:
        raw_value = getattr(value, "value", value)
        return raw_value if isinstance(raw_value, str) else str(raw_value)

    try:
        rhythm_model_path = os.getenv("ARR_RHYTHM_MODEL_PATH") or None
        beat_model_path = os.getenv("ARR_BEAT_MODEL_PATH") or None
        rhythm_model_type = os.getenv("ARR_RHYTHM_MODEL_TYPE") or "cnn"

        result = cast(InferenceResultLike, classify_ecg(
            signal=signal,
            fs=sampling_rate,
            target_fs=250,
            rpeak_method="hamilton",
            beat_model_path=beat_model_path,
            rhythm_model_path=rhythm_model_path,
            rhythm_model_type=rhythm_model_type,
            precomputed_rpeaks=precomputed_rpeaks,
            precomputed_fs=precomputed_fs if precomputed_fs is not None else sampling_rate,
        ))
        primary = _label_to_str(result.primary_rhythm)
        strip = _label_to_str(result.strip_label)
        display = _arr_display_names.get(primary, primary)
        return {
            "primary_rhythm":     primary,
            "display_name":       display,
            "strip_label":        strip,
            "confidence":         round(result.confidence, 3),
            "beat_labels":        result.beat_labels[:20],
            "used_deep_learning": result.used_deep_learning,
            "notes":              result.notes,
        }
    except (AttributeError, ValueError, RuntimeError, TypeError) as exc:
        logger.warning(f"Arrhythmia pipeline failed ({type(exc).__name__}): {exc}")
        return {"error": str(exc)}
