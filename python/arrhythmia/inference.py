"""
End-to-end arrhythmia inference pipeline.

Orchestrates: preprocess → detect R-peaks → segment → features → model → post-process

Public API
----------
classify_ecg(signal, fs, beat_model_path, rhythm_model_path, ...)
    -> InferenceResult

InferenceResult
    .primary_rhythm     : str (ArrhythmiaClass)
    .beat_labels        : list[str]  — per-beat predictions
    .strip_label        : str        — strip-level rhythm
    .confidence         : float
    .features           : dict
    .r_peaks            : np.ndarray
    .rr_ms              : np.ndarray
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

from arrhythmia.preprocess import preprocess
from arrhythmia.rpeaks import detect_and_compute
from arrhythmia.segments import extract_beat_windows, extract_rhythm_windows, pad_or_truncate
from arrhythmia.features import extract_strip_features
from arrhythmia.postprocess import smooth_predictions, apply_physiologic_constraints
from arrhythmia.constants import ArrhythmiaClass


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class InferenceResult:
    """Output of the arrhythmia inference pipeline."""

    primary_rhythm: str = ArrhythmiaClass.NSR
    strip_label: str = ArrhythmiaClass.NSR
    beat_labels: list[str] = field(default_factory=list)
    confidence: float = 0.0
    features: dict = field(default_factory=dict)
    r_peaks: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    rr_ms: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    used_deep_learning: bool = False
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Classical (rule-based) strip classification
# Uses pre-computed features when no model is available.
# ---------------------------------------------------------------------------

def _classical_classify(features: dict) -> tuple[str, float]:
    """
    Rule-based rhythm classification from extracted features.

    Returns (label, confidence).
    Low-confidence rules return 0.4–0.6; high-confidence rules return 0.7–0.9.
    This is intentionally conservative — use deep models for production.
    """
    hr = features.get("heart_rate_bpm", float("nan"))
    rr_cv = features.get("rr_cv", float("nan"))
    rr_rmssd = features.get("rr_rmssd", float("nan"))
    num_beats = features.get("num_beats", 0.0)
    signal_power = features.get("signal_power", float("nan"))
    # qrs_wide may be injected by _pipeline_from_measurements; None = unknown
    qrs_wide: bool | None = features.get("qrs_wide")
    # vf_morphology: explicitly set when image shows chaotic undulating baseline (no QRS)
    vf_morphology: bool | None = features.get("vf_morphology")

    import math

    def _nan(*vals) -> bool:
        return any(math.isnan(v) for v in vals)

    # VF morphology flag — check before ASYS because VF also has no regular beats
    if vf_morphology is True:
        return ArrhythmiaClass.VF, 0.82

    # Asystole — no beats detected or flat signal
    if num_beats < 2 or (not _nan(signal_power) and signal_power < 0.001):
        return ArrhythmiaClass.ASYS, 0.85

    if _nan(hr, rr_cv):
        return ArrhythmiaClass.NSR, 0.3

    # VF — chaotic, high power, no regular beats (signal-based; vf_morphology flag is preferred)
    if (not _nan(rr_cv) and rr_cv > 0.40 and
            not _nan(signal_power) and signal_power > 0.1):
        return ArrhythmiaClass.VF, 0.65

    # VT — fast + wide QRS (most specific rule when morphology is known)
    if hr > 100 and qrs_wide is True and not _nan(rr_cv) and rr_cv < 0.15:
        return ArrhythmiaClass.VT, 0.75

    # AF — irregularly irregular
    # At fast rates (>120 bpm), absolute RR variation is bounded, so thresholds scale down.
    # CV 0.10 / RMSSD 40 ms is sufficient evidence of irregularity at high ventricular rates.
    _af_cv_thresh   = 0.10 if (not _nan(hr) and hr > 120) else 0.15
    _af_rmssd_thresh = 40.0 if (not _nan(hr) and hr > 120) else 60.0
    if not _nan(rr_cv, rr_rmssd) and rr_cv > _af_cv_thresh and rr_rmssd > _af_rmssd_thresh:
        return ArrhythmiaClass.AF, 0.70

    # AFL — very regular fast rate (~150 bpm from 2:1 block)
    if 140 <= hr <= 165 and not _nan(rr_cv) and rr_cv < 0.05:
        return ArrhythmiaClass.AFL, 0.65

    # SVT — very fast, narrow (or unknown QRS width), regular
    if hr > 150 and not _nan(rr_cv) and rr_cv < 0.10 and qrs_wide is not True:
        return ArrhythmiaClass.SVT, 0.60

    # Sinus Tachycardia
    if hr > 100:
        return ArrhythmiaClass.ST, 0.75

    # Sinus Bradycardia
    if hr < 60:
        return ArrhythmiaClass.SB, 0.75

    # Normal Sinus Rhythm
    return ArrhythmiaClass.NSR, 0.80


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def classify_ecg(
    signal: np.ndarray,
    fs: int,
    target_fs: int = 250,
    rpeak_method: str = "hamilton",
    beat_model_path: Optional[str | Path] = None,
    rhythm_model_path: Optional[str | Path] = None,
    rhythm_model_type: str = "cnn",
    beat_window_pre_ms: float = 200.0,
    beat_window_post_ms: float = 400.0,
    rhythm_window_s: float = 10.0,
    smooth_window: int = 5,
) -> InferenceResult:
    """
    Full inference pipeline from raw ECG signal to arrhythmia classification.

    Parameters
    ----------
    signal              : raw 1-D ECG signal (any sampling rate)
    fs                  : sampling rate of input signal (Hz)
    target_fs           : resample to this rate (Hz), default 250
    rpeak_method        : R-peak detector ('hamilton', 'pantompkins', 'wfdb')
    beat_model_path     : path to BeatCNN checkpoint (.pt); None = classical only
    rhythm_model_path   : path to rhythm model checkpoint (.pt); None = classical only
    rhythm_model_type   : 'cnn', 'rnn', or 'transformer'
    beat_window_pre_ms  : pre-R window for beat segmentation (ms)
    beat_window_post_ms : post-R window for beat segmentation (ms)
    rhythm_window_s     : rhythm strip duration (seconds)
    smooth_window       : smoothing window size for post-processing

    Returns
    -------
    InferenceResult
    """
    result = InferenceResult()
    notes: list[str] = []

    # ------------------------------------------------------------------
    # Step 1 — Preprocess
    # ------------------------------------------------------------------
    processed, eff_fs = preprocess(signal, fs, target_fs=target_fs)

    # ------------------------------------------------------------------
    # Step 2 — R-peak detection
    # ------------------------------------------------------------------
    r_peaks, rr_ms = detect_and_compute(processed, eff_fs, method=rpeak_method)
    result.r_peaks = r_peaks
    result.rr_ms = rr_ms

    if len(r_peaks) == 0:
        result.primary_rhythm = ArrhythmiaClass.ASYS
        result.strip_label = ArrhythmiaClass.ASYS
        result.confidence = 0.85
        result.notes = ["No R-peaks detected — classified as Asystole"]
        return result

    # ------------------------------------------------------------------
    # Step 3 — Strip-level features (always computed)
    # ------------------------------------------------------------------
    strip_feats = extract_strip_features(processed, r_peaks, eff_fs)
    result.features = strip_feats

    # ------------------------------------------------------------------
    # Step 4a — Strip-level classification
    # ------------------------------------------------------------------
    strip_label = ArrhythmiaClass.NSR
    strip_confidence = 0.0

    if rhythm_model_path is not None:
        try:
            strip_label, strip_confidence = _dl_strip_classify(
                processed, eff_fs, rhythm_model_path,
                rhythm_model_type, rhythm_window_s, smooth_window,
            )
            result.used_deep_learning = True
        except Exception as exc:
            notes.append(f"Rhythm model failed ({exc}); falling back to classical")
            strip_label, strip_confidence = _classical_classify(strip_feats)
    else:
        strip_label, strip_confidence = _classical_classify(strip_feats)

    result.strip_label = strip_label

    # ------------------------------------------------------------------
    # Step 4b — Beat-level classification (PAC / PVC detection)
    # ------------------------------------------------------------------
    beat_windows = extract_beat_windows(
        processed, r_peaks, eff_fs,
        pre_ms=beat_window_pre_ms,
        post_ms=beat_window_post_ms,
    )
    beat_labels: list[str] = []

    if beat_model_path is not None:
        try:
            beat_labels = _dl_beat_classify(beat_windows, beat_model_path, eff_fs)
            result.used_deep_learning = True
        except Exception as exc:
            notes.append(f"Beat model failed ({exc}); beat labels unavailable")
    result.beat_labels = beat_labels

    # ------------------------------------------------------------------
    # Step 5 — Post-processing: physiologic constraints
    # ------------------------------------------------------------------
    final_rhythm = apply_physiologic_constraints(
        strip_label=strip_label,
        beat_labels=beat_labels,
    )

    result.primary_rhythm = final_rhythm
    result.confidence = strip_confidence
    result.notes = notes
    return result


# ---------------------------------------------------------------------------
# Deep learning helpers
# ---------------------------------------------------------------------------

def _dl_strip_classify(
    signal: np.ndarray,
    fs: int,
    model_path: str | Path,
    model_type: str,
    window_s: float,
    smooth_window: int,
) -> tuple[str, float]:
    """Run strip-level DL model and return (label, confidence)."""
    from arrhythmia.models.rhythm_model import RhythmCNN, RhythmRNN, RhythmTransformer

    input_len = int(window_s * fs)
    model_cls = {"cnn": RhythmCNN, "rnn": RhythmRNN, "transformer": RhythmTransformer}[model_type]
    model = model_cls.from_checkpoint(model_path, input_len=input_len)

    strips = extract_rhythm_windows(signal, fs, window_s=window_s)
    predictions = model.predict_numpy(strips)

    labels = [p["label"] for p in predictions]
    confs  = [p["confidence"] for p in predictions]

    smoothed = smooth_predictions(labels, window=smooth_window)
    final = _majority_vote(smoothed)
    avg_conf = float(np.mean([c for l, c in zip(labels, confs) if l == final] or confs))
    return final, avg_conf


def _dl_beat_classify(
    beat_windows: list[np.ndarray],
    model_path: str | Path,
    fs: int,
) -> list[str]:
    """Run beat-level DL model and return list of per-beat labels."""
    from arrhythmia.models.beat_model import BeatCNN

    # Default input length: 150 samples at 250 Hz ≈ 600 ms
    input_len = 150
    model = BeatCNN.from_checkpoint(model_path, num_classes=3, input_len=input_len)
    predictions = model.predict_numpy(beat_windows)
    return [p["label"] for p in predictions]


def _majority_vote(labels: list[str]) -> str:
    if not labels:
        return ArrhythmiaClass.NSR
    from collections import Counter
    return Counter(labels).most_common(1)[0][0]
