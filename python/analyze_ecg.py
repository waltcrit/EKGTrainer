#!/usr/bin/env python3
"""
ECG analysis pipeline: image -> digitized signal -> BioSPPy measurements -> JSON stdout.

Usage:
    python analyze_ecg.py --image /tmp/ecg.png
    python analyze_ecg.py --image /tmp/ecg.png --leads 12

Output: JSON object written to stdout, errors to stderr.
Exit code 0 = success, 1 = failure.
"""

import argparse
import importlib
import json
import logging
import sys
import traceback
from pathlib import Path
from typing import Any, NotRequired, Protocol, TypeAlias, TypedDict, cast

import numpy as np
import json as _json_module
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


SignalArray: TypeAlias = NDArray[np.float64]
SignalMap: TypeAlias = dict[str, SignalArray]


class DigitizedResult(TypedDict):
    signals: SignalMap
    sampling_rate: int
    method: str
    calibrated: bool          # True when pixels_per_mv was used for true-mV scaling


class STLeadResult(TypedDict):
    elevation: bool
    depression: bool
    mean_mv: float


STResults: TypeAlias = dict[str, STLeadResult]


class PipelineClassification(TypedDict, total=False):
    primary_rhythm: str
    display_name: str
    strip_label: str
    confidence: float
    beat_labels: list[str]
    used_deep_learning: bool
    notes: list[str]
    error: str


class SignalMeasurements(TypedDict):
    r_peaks: list[int]
    rr_intervals_ms: list[float]
    heart_rate_bpm: float
    regularity: str
    p_waves_present: bool
    p_wave_morphology: NotRequired[str | None]   # "upright"|"inverted"|"biphasic"|None
    pr_interval_ms: float | None
    qrs_duration_ms: float | None
    qrs_wide: bool
    qt_ms: float | None
    qtc_ms: float | None                         # Bazett
    qtcf_ms: NotRequired[float | None]           # Fridericia
    qtc_method: NotRequired[str]                 # which formula was used for prolonged flag
    qtc_prolonged: bool | None
    st: STResults
    num_beats: int
    rhythm_lead: str
    amplitude_calibrated: NotRequired[bool]      # True when signal is in true mV
    afib_hint: NotRequired[bool]                 # irregularly irregular + no P-waves
    vf_morphology: NotRequired[bool]


class InferenceResultLike(Protocol):
    primary_rhythm: object
    strip_label: object
    confidence: float
    beat_labels: list[str]
    used_deep_learning: bool
    notes: list[str]

# ---------------------------------------------------------------------------
# Arrhythmia pipeline — optional; degrades gracefully if not importable
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

# ---------------------------------------------------------------------------
# Hoisted lazy imports — avoid per-call module lookup overhead
# ---------------------------------------------------------------------------
try:
    import cv2
    _cv2_available = True
except ImportError:
    _cv2_available = False

try:
    import scipy.ndimage as scipy_ndimage
    _scipy_ndimage_available = True
except ImportError:
    _scipy_ndimage_available = False

try:
    import biosppy.signals.ecg as bsp_ecg_module
    _biosppy_available = True
except ImportError:
    _biosppy_available = False

try:
    from ecg_digitiser.digitiser import ECGDigitiser
    _ecg_digitiser_available = True
except ImportError:
    _ecg_digitiser_available = False


class _NumpyEncoder(_json_module.JSONEncoder):
    """Serialize numpy scalars and arrays to native Python types."""
    def default(self, o: object) -> object:
        if isinstance(o, np.integer):
            return int(cast(int, o))
        if isinstance(o, np.floating):
            return float(cast(float, o))
        if isinstance(o, np.bool_):
            return bool(cast(bool, o))
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


NumpyEncoder = _NumpyEncoder


def _dumps(obj: object) -> str:
    return _json_module.dumps(obj, cls=_NumpyEncoder)


# ---------------------------------------------------------------------------
# Step 1 — Image digitization
# ---------------------------------------------------------------------------

def digitize_image(image_path: str | None = None, image_bytes: bytes | None = None) -> DigitizedResult:
    """
    Convert an ECG image to a digital signal using ECG-Digitiser or OpenCV fallback.
    Accepts either a file path or raw image bytes.
    Returns a dict with keys: signals (dict of lead->np.ndarray), sampling_rate (int).
    """
    if image_path is None and image_bytes is None:
        raise ValueError("Either image_path or image_bytes must be provided")

    if _ecg_digitiser_available and image_path is not None:
        try:
            digitiser = ECGDigitiser()
            result = digitiser.digitise(image_path)
            signals = {
                str(lead): np.asarray(values, dtype=np.float64)
                for lead, values in cast(dict[object, object], result.signals).items()
            }
            return {
                "signals": signals,
                "sampling_rate": int(result.sampling_rate),
                "method": "ecg-digitiser",
                "calibrated": True,  # ECG-Digitiser outputs calibrated mV
            }
        except Exception as e:
            logger.warning(f"ECG-Digitiser failed: {type(e).__name__}: {e}; falling back to OpenCV")

    return _fallback_digitize(image_path, image_bytes)


def _detect_grid_calibration(gray: NDArray[np.uint8]) -> dict[str, float] | None:
    """
    Detect ECG paper grid spacing using FFT on row/column projections.

    Standard ECG paper: 25 mm/s, 10 mm/mV.
    Small squares: 1 mm = 40 ms horizontal, 0.1 mV vertical.

    Returns dict with keys: sampling_rate_hz, pixels_per_mv, grid_px_horiz.
    Returns None if grid cannot be confidently detected.
    """
    _, w = gray.shape

    # ── Horizontal axis (time) ────────────────────────────────────────────
    col_sum = gray.astype(float).sum(axis=0)
    col_sum -= col_sum.mean()
    fft_h = np.abs(np.fft.rfft(col_sum))
    freqs_h = np.fft.rfftfreq(w)

    # Search for the 1 mm small-square period: typically 4–25 px at 96–300 dpi
    with np.errstate(divide="ignore", invalid="ignore"):
        periods_h = np.where(freqs_h > 0, 1.0 / freqs_h, np.inf)
    mask_h = (4 < periods_h) & (periods_h < 25)
    if not mask_h.any():
        return None
    grid_px_horiz = float(periods_h[np.argmax(fft_h * mask_h)])

    # Confidence check: peak should be meaningfully above neighbours
    peak_mag = float(np.max(fft_h * mask_h))
    mean_mag = float(np.mean(fft_h[mask_h]))
    if peak_mag < mean_mag * 3:
        return None  # no clear periodic signal

    # 1 mm small square = 40 ms at 25 mm/s
    sampling_rate_hz = grid_px_horiz / 0.040

    # ── Vertical axis (amplitude) ─────────────────────────────────────────
    # If vertical grid detection is unreliable, derive from horizontal
    # (both axes share the same mm/px ratio on square-grid paper).
    # pixels_per_mv = px_per_mm × 10 mm/mV = grid_px_horiz × 10
    pixels_per_mv = grid_px_horiz * 10.0

    return {
        "sampling_rate_hz": sampling_rate_hz,
        "pixels_per_mv":    pixels_per_mv,
        "grid_px_horiz":    grid_px_horiz,
    }


def _fallback_digitize(image_path: str | None = None, image_bytes: bytes | None = None) -> DigitizedResult:
    """
    Grid-calibrated OpenCV digitizer.

    Accepts either image_path or image_bytes.
    Detects the ECG paper grid via FFT to determine the true sampling rate,
    then traces the waveform and normalizes the signal for BioSPPy.
    """
    if not _cv2_available:
        raise RuntimeError(
            "opencv-python is not installed. Cannot digitize ECG image."
        )

    if image_bytes is not None:
        img_bgr = cast(NDArray[np.uint8] | None, cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR))
        if img_bgr is None:
            raise RuntimeError("Could not decode image bytes")
    elif image_path is not None:
        img_bgr = cast(NDArray[np.uint8] | None, cv2.imread(image_path))
        if img_bgr is None:
            raise RuntimeError(f"Could not read image: {image_path}")
    else:
        raise ValueError("Either image_path or image_bytes must be provided")

    gray = cast(NDArray[np.uint8], cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY))
    h, w = gray.shape

    # ── Step 1: calibrate sampling rate and amplitude from grid ──────────
    cal = _detect_grid_calibration(gray)
    if cal:
        sampling_rate = int(round(cal["sampling_rate_hz"]))
        pixels_per_mv = cal["pixels_per_mv"]
        method = f"fallback-opencv-calibrated({sampling_rate}Hz)"
        calibrated = True
    else:
        sampling_rate = 179   # observed default across our image set
        pixels_per_mv = None
        method = "fallback-opencv-uncalibrated"
        calibrated = False

    # Cap to a physically plausible digitised-image range.
    # Very high rates (>600 Hz) cause BioSPPy to build impractically long
    # FIR filters whose padlen exceeds the signal length.
    sampling_rate = min(sampling_rate, 500)

    # ── Step 2: isolate and trace the ECG waveform ────────────────────────
    # Invert so the dark ECG trace becomes the brightest feature per column.
    inv = (255 - gray).astype(float)

    # Trim the leftmost and rightmost 1% of columns — they often contain
    # border lines or labels that would be picked up by argmax.
    margin = max(1, w // 100)
    inv[:, :margin]  = 0
    inv[:, -margin:] = 0

    # Also zero out the top and bottom 5% of rows to ignore frame borders.
    v_margin = max(1, h // 20)
    inv[:v_margin, :] = 0
    inv[-v_margin:, :] = 0

    # For each column, find the row of the darkest (brightest-after-invert) pixel.
    trace_row = np.argmax(inv, axis=0).astype(float)

    # Smooth out single-pixel jumps caused by ECG grid-line crossings.
    # A 3-sample median preserves sharp R-peaks while eliminating 1-pixel spikes.
    if not _scipy_ndimage_available:
        raise RuntimeError("scipy is not installed. Cannot digitize ECG image.")
    trace_row = scipy_ndimage.median_filter(trace_row, size=3).astype(float)

    # Flip: row 0 is top of image; upward deflections → smaller row index.
    signal = (h - 1) - trace_row

    # ── Step 3: baseline-correct and scale to mV ─────────────────────────
    # Remove slow baseline wander with a wide median filter.
    median_filter_fn = scipy_ndimage.median_filter
    bl_window = max(3, int(sampling_rate * 0.6) | 1)  # must be odd
    baseline = cast(SignalArray, median_filter_fn(signal, size=bl_window, mode="nearest"))
    signal = signal - baseline

    if calibrated and pixels_per_mv is not None and pixels_per_mv > 0:
        # Scale to true mV using grid-detected calibration so downstream
        # ST thresholds and amplitude measurements are clinically meaningful.
        signal = signal / pixels_per_mv
    elif signal.std() > 0:
        # Fallback normalization when grid calibration is unavailable.
        # Amplitude is no longer clinically meaningful; caveats apply to ST.
        signal = signal / signal.std() * 0.5

    # ── Step 4: pacing-artifact suppression ───────────────────────────────
    # Interpolate over very narrow, isolated extreme-amplitude spikes.
    # Width guard: ≤2 samples only (12 ms at 150 Hz) — avoids erasing narrow
    # QRS complexes, notches, or J-waves in legitimate beats.
    spike_thr = float(np.percentile(np.abs(signal), 99.5)) * 2.0
    spike_mask = np.abs(signal) > spike_thr
    labeled_spikes, n_spikes = scipy_ndimage.label(spike_mask)
    for spike_id in range(1, n_spikes + 1):
        spike_idx = np.where(labeled_spikes == spike_id)[0]
        if len(spike_idx) <= 2:   # ≤2-sample spike = pacing artifact
            lo_i = max(0, spike_idx[0] - 1)
            hi_i = min(len(signal) - 1, spike_idx[-1] + 1)
            signal[spike_idx] = np.interp(
                spike_idx.astype(float),
                [float(lo_i), float(hi_i)],
                [signal[lo_i], signal[hi_i]],
            )

    return {
        "signals":    {"II": signal},
        "sampling_rate": sampling_rate,
        "method":     method,
        "calibrated": calibrated,
    }


# ---------------------------------------------------------------------------
# Step 2 — Signal processing with BioSPPy
# ---------------------------------------------------------------------------

def analyze_signal(
    signals: SignalMap,
    sampling_rate: int,
    calibrated: bool = False,
) -> SignalMeasurements:
    """
    Run BioSPPy ECG analysis on the digitized signals.
    Picks the lead with the highest mean R-peak amplitude for rhythm metrics,
    and runs per-lead ST/T analysis when multiple leads are present.
    """
    if not _biosppy_available:
        raise RuntimeError(
            "biosppy is not installed. Cannot analyze ECG signal."
        )

    # Pick rhythm lead by highest RMS amplitude — more diagnostic than hardcoding Lead II.
    # Lead II is still preferred when it ties, as it gives the clearest P-waves clinically.
    def _lead_rms(sig: SignalArray) -> float:
        return float(np.sqrt(np.mean(sig ** 2)))

    rhythm_lead_name = max(
        signals,
        key=lambda lead: _lead_rms(signals[lead]) * (1.05 if lead == "II" else 1.0),
    )
    rhythm_signal = signals[rhythm_lead_name]

    # BioSPPy needs at least a few seconds of signal
    if len(rhythm_signal) < sampling_rate * 2:
        raise RuntimeError(
            f"Signal too short ({len(rhythm_signal)} samples at {sampling_rate} Hz). "
            "Need at least 2 seconds."
        )

    templates_raw: object = None
    try:
        out = cast(dict[str, object], bsp_ecg_module.ecg(
            signal=rhythm_signal,
            sampling_rate=sampling_rate,
            show=False,
        ))
        r_peaks = np.asarray(out["rpeaks"], dtype=np.int64)
        try:
            templates_raw = out["templates"]
        except KeyError:
            templates_raw = None
    except (ValueError, RuntimeError, TypeError) as e:
        logger.warning(f"BioSPPy ECG detection failed ({type(e).__name__}); falling back to scipy")
        from scipy.signal import find_peaks as _sp_find_peaks  # type: ignore
        min_dist = max(1, int(sampling_rate * 0.25))   # >= 250 ms between beats
        thresh   = float(np.percentile(rhythm_signal, 65))
        peak_idx, _ = _sp_find_peaks(
            rhythm_signal, height=thresh, distance=min_dist
        )
        r_peaks = np.asarray(peak_idx, dtype=np.int64)
        templates_raw = None

    r_peaks = _clean_r_peaks(r_peaks, rhythm_signal, sampling_rate)

    rr_intervals_ms = _rr_intervals(r_peaks, sampling_rate)
    heart_rate_bpm = _mean_hr(rr_intervals_ms)
    regularity = _regularity(rr_intervals_ms)

    # Rate sanity cross-check with scipy.
    # Trigger when BioSPPy gives a physiologically implausible result (>280 bpm
    # or < 20 bpm with enough signal present), or found almost no peaks.
    _implausible = (
        heart_rate_bpm > 280
        or heart_rate_bpm < 20
        or (len(r_peaks) < 3 and len(rhythm_signal) > sampling_rate * 5)
    )
    if _implausible:
        from scipy.signal import find_peaks as _sp_cv  # type: ignore
        cv_dist = max(1, int(sampling_rate * 0.27))   # >= 270 ms -> max ~220 bpm
        for _pct in (85, 75, 65):
            _cv_thresh = float(np.percentile(rhythm_signal, _pct))
            _cv_peaks, _ = _sp_cv(rhythm_signal, height=_cv_thresh, distance=cv_dist)
            _cv_rr = _rr_intervals(np.asarray(_cv_peaks, dtype=np.int64), sampling_rate)
            _cv_hr = _mean_hr(_cv_rr)
            if 20 < _cv_hr < 280 and len(_cv_peaks) >= 2:
                r_peaks = np.asarray(_cv_peaks, dtype=np.int64)
                r_peaks = _clean_r_peaks(r_peaks, rhythm_signal, sampling_rate)
                rr_intervals_ms = _cv_rr
                heart_rate_bpm = _cv_hr
                regularity = _regularity(_cv_rr)
                break

    # QRS width: measure each template (BioSPPy supplies beat templates)
    templates = np.asarray(templates_raw, dtype=np.float64) if templates_raw is not None else None

    # Cache median template once and reuse in all downstream helpers
    median_template = np.median(templates, axis=0) if templates is not None and len(templates) > 0 else None

    qrs_ms, qrs_wide = _qrs_width(median_template, sampling_rate)

    # J-point offset from R-peak (used for accurate ST measurement)
    j_offset = _detect_j_point(median_template, sampling_rate)

    # P-wave / PR interval with polarity detection
    pr_ms, p_present, p_morphology = _pr_interval(median_template, sampling_rate, calibrated)

    # QT/QTc with derivative Q-onset and dual Bazett/Fridericia
    qt_ms, qtc_ms, qtcf_ms, qtc_prolonged, qtc_method = _qtc(
        median_template, rr_intervals_ms, sampling_rate, heart_rate_bpm
    )

    # ST segment (per lead, J-point aware, lead-specific thresholds)
    st_results = _st_analysis(signals, r_peaks, sampling_rate, j_offset)

    # AFib hint: irregularly irregular rhythm with absent P-waves
    # Supports the arrhythmia pipeline when unavailable and guides Claude prompt.
    afib_hint = (regularity == "irregularly_irregular") and not p_present

    return {
        "r_peaks": r_peaks.tolist(),
        "rr_intervals_ms": [round(x, 1) for x in rr_intervals_ms],
        "heart_rate_bpm": round(heart_rate_bpm, 1),
        "regularity": regularity,
        "p_waves_present": p_present,
        "p_wave_morphology": p_morphology,
        "pr_interval_ms": round(pr_ms, 1) if pr_ms is not None else None,
        "qrs_duration_ms": round(qrs_ms, 1) if qrs_ms is not None else None,
        "qrs_wide": qrs_wide,
        "qt_ms": round(qt_ms, 1) if qt_ms is not None else None,
        "qtc_ms": round(qtc_ms, 1) if qtc_ms is not None else None,
        "qtcf_ms": round(qtcf_ms, 1) if qtcf_ms is not None else None,
        "qtc_method": qtc_method,
        "qtc_prolonged": qtc_prolonged,
        "st": st_results,
        "num_beats": len(r_peaks),
        "rhythm_lead": rhythm_lead_name,
        "amplitude_calibrated": calibrated,
        "afib_hint": afib_hint,
    }


def _rr_intervals(r_peaks: np.ndarray, fs: int) -> list[float]:
    if len(r_peaks) < 2:
        return []
    return [(r_peaks[i + 1] - r_peaks[i]) / fs * 1000 for i in range(len(r_peaks) - 1)]


def _mean_hr(rr_ms: list[float]) -> float:
    if not rr_ms:
        return 0.0
    return float(60000.0 / np.mean(rr_ms))


def _clean_r_peaks(
    r_peaks: np.ndarray,
    signal: NDArray[np.float64],
    fs: int,
) -> np.ndarray:
    """Remove likely duplicate/spurious R-peaks from digitized traces."""
    if len(r_peaks) < 3:
        return np.asarray(r_peaks, dtype=np.int64)

    peaks = np.unique(np.asarray(r_peaks, dtype=np.int64))
    if len(peaks) < 3:
        return peaks

    changed = True
    while changed and len(peaks) >= 3:
        changed = False
        rr = np.diff(peaks)
        med_rr = float(np.median(rr)) if len(rr) else 0.0
        if med_rr <= 0:
            break

        close_idx = np.where(rr < med_rr * 0.45)[0]
        if len(close_idx) == 0:
            break

        keep = np.ones(len(peaks), dtype=bool)
        for i in close_idx:
            p0 = peaks[i]
            p1 = peaks[i + 1]
            a0 = abs(float(signal[p0]))
            a1 = abs(float(signal[p1]))
            if a0 >= a1:
                keep[i + 1] = False
            else:
                keep[i] = False

        new_peaks = peaks[keep]
        changed = len(new_peaks) != len(peaks)
        peaks = new_peaks

    return peaks.astype(np.int64)


def _regularity(rr_ms: list[float]) -> str:
    if len(rr_ms) < 3:
        return "indeterminate"
    arr = np.array(rr_ms)
    median_rr = float(np.median(arr))
    # Discard extreme outliers (e.g. digitizer-artifact intervals) before
    # measuring spread; a valid beat interval should be within 40%–250% of
    # the median.
    valid = arr[(arr > median_rr * 0.40) & (arr < median_rr * 2.50)]
    if len(valid) < 2:
        valid = arr

    # If most intervals cluster tightly around a dominant cycle length,
    # treat as regular despite a few artifact outliers.
    cluster_ratio = float(np.mean(np.abs(valid - median_rr) <= median_rr * 0.12))
    if cluster_ratio >= 0.72:
        return "regular"

    mean_v = float(np.mean(valid))
    cv = float(np.std(valid) / mean_v) if mean_v > 0 else 1.0
    # 8% CV threshold (vs original 5%) tolerates minor digitizer jitter on
    # otherwise regular rhythms.
    if cv < 0.08:
        return "regular"
    diffs = np.diff(valid)
    if len(diffs) >= 2 and float(np.std(diffs)) < float(np.std(valid)) * 0.55:
        return "regularly_irregular"
    return "irregularly_irregular"


def _detect_j_point(median_template: NDArray[np.float64] | None, fs: int) -> int:
    """
    Estimate J-point offset (in samples) relative to R-peak in the median template.
    The J-point is the end of the QRS complex where ST segment begins.
    Returns a safe default of 40 ms if detection fails.
    """
    default = max(1, int(0.04 * fs))  # 40 ms fallback
    if median_template is None or len(median_template) == 0:
        return default

    mid = len(median_template) // 2
    # Search 10–120 ms after R-peak for where QRS energy drops below 15% of R-peak energy
    search_end = min(len(median_template), mid + int(0.12 * fs))
    post_r = median_template[mid:search_end]

    if len(post_r) == 0:
        return default

    r_energy = float(median_template[mid] ** 2)
    if r_energy == 0:
        return default

    energy = post_r ** 2
    # Walk forward from R until energy drops below 15% of R energy — that is J-point
    below = np.where(energy < r_energy * 0.15)[0]
    if len(below) == 0:
        return default

    j_offset = int(below[0])
    # Clamp to physiologically plausible 20–100 ms range
    return max(int(0.02 * fs), min(j_offset, int(0.10 * fs)))


def _qrs_width(median_template: NDArray[np.float64] | None, fs: int) -> tuple[float | None, bool]:
    """
    Estimate QRS duration from median beat template.
    Searches only within a ±80 ms window around R-peak to avoid
    including T-wave energy that inflates the measurement.
    """
    if median_template is None or len(median_template) == 0:
        return None, False
    mid = len(median_template) // 2
    # Constrain to ±80 ms QRS window to exclude P and T waves
    qrs_start = max(0, mid - int(0.08 * fs))
    qrs_end = min(len(median_template), mid + int(0.08 * fs))
    qrs_region = median_template[qrs_start:qrs_end]

    energy = qrs_region ** 2
    peak_energy = float(energy.max())
    if peak_energy == 0:
        return None, False

    threshold = peak_energy * 0.1
    above = np.where(energy > threshold)[0]
    if len(above) < 2:
        return None, False
    width_samples = above[-1] - above[0]
    width_ms = width_samples / fs * 1000
    return width_ms, width_ms >= 120


def _pr_interval(
    median_template: NDArray[np.float64] | None,
    fs: int,
    calibrated: bool = False,
) -> tuple[float | None, bool, str | None]:
    """
    Estimate PR interval and P-wave presence/morphology from median beat template.
    BioSPPy centres templates on the R peak; P wave appears ~100–200 ms before.

    Returns (pr_ms, p_present, morphology) where morphology is one of:
      "upright" | "inverted" | "biphasic" | None
    """
    if median_template is None or len(median_template) == 0:
        return None, False, None

    tmpl = median_template
    mid = len(tmpl) // 2

    # Look in the 50–250 ms window before R-peak for a P deflection
    pre_start = max(0, mid - int(0.25 * fs))
    pre_end = max(0, mid - int(0.05 * fs))
    pre_region = tmpl[pre_start:pre_end]

    if len(pre_region) == 0:
        return None, False, None

    # Amplitude thresholds: absolute 0.1 mV when calibrated; 10% of R when not.
    r_amp = float(np.max(np.abs(tmpl[max(0, mid - 5):mid + 5]))) if mid >= 5 else float(np.max(np.abs(tmpl)))
    threshold = 0.10 if (calibrated and r_amp > 0.10) else r_amp * 0.10

    pos_peak = float(np.max(pre_region))
    neg_peak = float(np.min(pre_region))

    has_pos = pos_peak > threshold
    has_neg = abs(neg_peak) > threshold

    if not has_pos and not has_neg:
        return None, False, None

    # Classify polarity
    if has_pos and has_neg:
        morphology = "biphasic"
        # Use absolute deflection to find dominant peak for PR distance
        p_peak_idx = pre_start + int(np.argmax(np.abs(pre_region)))
    elif has_pos:
        morphology = "upright"
        p_peak_idx = pre_start + int(np.argmax(pre_region))
    else:
        morphology = "inverted"
        p_peak_idx = pre_start + int(np.argmin(pre_region))

    pr_samples = mid - p_peak_idx
    pr_ms = pr_samples / fs * 1000
    return pr_ms, True, morphology


def _qtc(
    median_template: NDArray[np.float64] | None,
    rr_ms: list[float],
    fs: int,
    heart_rate_bpm: float = 75.0,
) -> tuple[float | None, float | None, float | None, bool | None, str]:
    """
    Estimate QT interval and rate-corrected QTc from the median beat template.

    Q-onset is derived from the first energy rise before R-peak (not a fixed 40 ms).
    Reports both Bazett (QT/√RR) and Fridericia (QT/∛RR) formulae.
    Selects the appropriate formula for the prolonged flag:
      - Bazett for 60–100 bpm (most validated range)
      - Fridericia for HR > 100 or < 60 (Bazett over/under-corrects at extremes)

    Returns (qt_ms, qtc_bazett_ms, qtc_fridericia_ms, prolonged, method_used).
    """
    if median_template is None or len(median_template) == 0 or not rr_ms:
        return None, None, None, None, "bazett"

    tmpl = median_template
    mid = len(tmpl) // 2

    # ── Q-onset: energy-based, not fixed 40 ms ───────────────────────────
    pre_r_start = max(0, mid - int(0.10 * fs))  # look up to 100 ms before R
    pre_r = tmpl[pre_r_start:mid]
    if len(pre_r) > 0:
        pre_energy = pre_r ** 2
        peak_pre = float(pre_energy.max())
        if peak_pre > 0:
            above_pre = np.where(pre_energy > peak_pre * 0.10)[0]
            q_onset_in_window = int(above_pre[0]) if len(above_pre) > 0 else len(pre_r) - int(0.04 * fs)
            q_onset_idx = pre_r_start + q_onset_in_window
        else:
            q_onset_idx = mid - int(0.04 * fs)
    else:
        q_onset_idx = mid - int(0.04 * fs)

    # ── T-wave end: last sample above 10% of T-peak ───────────────────────
    post_start = mid + int(0.05 * fs)
    post_end = min(len(tmpl), mid + int(0.55 * fs))
    post_region = tmpl[post_start:post_end]

    if len(post_region) == 0:
        return None, None, None, None, "bazett"

    t_peak = float(np.max(np.abs(post_region)))
    above = np.where(np.abs(post_region) > t_peak * 0.10)[0]
    if len(above) == 0:
        return None, None, None, None, "bazett"

    t_end_idx = post_start + int(above[-1])
    qt_samples = t_end_idx - q_onset_idx
    qt_ms = qt_samples / fs * 1000

    # ── Rate correction ────────────────────────────────────────────────────
    rr_sec = float(np.mean(rr_ms)) / 1000.0
    if rr_sec <= 0:
        return qt_ms, None, None, None, "bazett"

    qtc_bazett = qt_ms / (rr_sec ** 0.5)
    qtc_fridericia = qt_ms / (rr_sec ** (1.0 / 3.0))

    # Choose the more accurate formula for the prolonged flag based on rate
    if heart_rate_bpm > 100 or heart_rate_bpm < 60:
        qtc_primary = qtc_fridericia
        method = "fridericia"
    else:
        qtc_primary = qtc_bazett
        method = "bazett"

    prolonged = qtc_primary > 450

    return qt_ms, qtc_bazett, qtc_fridericia, prolonged, method


# AHA-aligned ST elevation thresholds (mV) by lead.
# V2/V3 have higher thresholds due to normal early repolarization variants.
# All other leads default to 0.1 mV. (AHA/ACC 2013 STEMI guidelines)
_ST_ELEVATION_THRESHOLDS: dict[str, float] = {
    "V2": 0.20,
    "V3": 0.20,
}
_ST_ELEVATION_DEFAULT = 0.10
_ST_DEPRESSION_THRESHOLD = 0.05  # uniform 0.5 mm across all leads


def _st_analysis(
    signals: SignalMap,
    r_peaks: np.ndarray,
    fs: int,
    j_offset_samples: int = 0,
) -> STResults:
    """
    ST segment analysis across all available leads.

    Measures at J-point + 80 ms (the clinical standard).
    Subtracts the PR-segment isoelectric baseline (50–20 ms before R-peak)
    to neutralize baseline drift from digitization.
    Uses AHA-aligned lead-specific elevation thresholds.
    """
    st_offset = j_offset_samples + int(0.08 * fs)  # J + 80 ms
    pr_start = int(0.05 * fs)   # 50 ms before R
    pr_end = int(0.02 * fs)     # 20 ms before R
    results: STResults = {}

    for lead, sig in signals.items():
        if len(r_peaks) == 0:
            results[lead] = {"elevation": False, "depression": False, "mean_mv": 0.0}
            continue

        st_vals: list[float] = []
        for rp in r_peaks:
            st_idx = rp + st_offset
            if st_idx >= len(sig):
                continue
            # PR-segment baseline reference for this beat
            bl_start = max(0, rp - pr_start)
            bl_end = max(0, rp - pr_end)
            baseline = float(np.mean(sig[bl_start:bl_end])) if bl_end > bl_start else 0.0
            st_vals.append(float(sig[st_idx]) - baseline)

        if not st_vals:
            continue

        mean_st = float(np.mean(st_vals))
        elev_thresh = _ST_ELEVATION_THRESHOLDS.get(lead, _ST_ELEVATION_DEFAULT)
        results[lead] = {
            "elevation": mean_st > elev_thresh,
            "depression": mean_st < -_ST_DEPRESSION_THRESHOLD,
            "mean_mv": round(mean_st, 3),
        }

    return results


# ---------------------------------------------------------------------------
# Step 3a — PhysioNet pipeline pre-classification
# ---------------------------------------------------------------------------

def run_pipeline_classification(
    signals: SignalMap,
    sampling_rate: int,
) -> PipelineClassification | None:
    """
    Run the arrhythmia.inference pipeline on the Lead II signal and return
    a structured result dict, or None if the pipeline is unavailable.

    The result is included in the server response and used as a hint inside
    the Claude prompt so the LLM can confirm or override the signal-derived
    classification.
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
        result = cast(InferenceResultLike, classify_ecg(
            signal=signal,
            fs=sampling_rate,
            target_fs=250,
            rpeak_method="hamilton",
        ))
        primary = _label_to_str(result.primary_rhythm)
        strip = _label_to_str(result.strip_label)
        display = _arr_display_names.get(primary, primary)
        return {
            "primary_rhythm":  primary,
            "display_name":    display,
            "strip_label":     strip,
            "confidence":      round(result.confidence, 3),
            "beat_labels":     result.beat_labels[:20],   # cap for JSON size
            "used_deep_learning": result.used_deep_learning,
            "notes":           result.notes,
        }
    except (ValueError, RuntimeError, TypeError) as exc:
        logger.warning(f"Arrhythmia pipeline classification failed ({type(exc).__name__}): {exc}")
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Step 3b — Build Claude prompt from measurements
# ---------------------------------------------------------------------------

def build_claude_prompt(
    measurements: SignalMeasurements,
    digitizer_method: str,
    pipeline_classification: PipelineClassification | None = None,
) -> str:
    rr = measurements["rr_intervals_ms"]
    rr_str = ", ".join(f"{x:.0f}" for x in rr[:6]) if rr else "unavailable"

    st_lines: list[str] = []
    for lead, v in measurements["st"].items():
        if v["elevation"]:
            st_lines.append(f"  {lead}: elevated ({v['mean_mv']:+.2f} mV)")
        elif v["depression"]:
            st_lines.append(f"  {lead}: depressed ({v['mean_mv']:+.2f} mV)")
    st_summary = "\n".join(st_lines) if st_lines else "  No significant ST deviation detected"

    # Build the optional pipeline pre-classification block
    if pipeline_classification and "error" not in pipeline_classification:
        pc = pipeline_classification
        hint_lines: list[str] = [
            "",
            "SIGNAL PIPELINE PRE-CLASSIFICATION (PhysioNet-compatible detector):",
            f"- Primary rhythm: {pc.get('display_name', pc.get('primary_rhythm', 'unknown'))} ({pc.get('primary_rhythm', '?')})",
            f"- Confidence: {pc.get('confidence', 0.0):.0%}",
        ]
        notes = pc.get("notes")
        if notes:
            hint_lines.append(f"- Notes: {'; '.join(notes)}")
        hint_lines += [
            "You may confirm or override this classification based on morphology and context.",
            "",
        ]
        pipeline_hint = "\n".join(hint_lines)
    else:
        pipeline_hint = ""

    # Build calibration caveat if amplitudes are uncalibrated
    amp_calibrated = measurements.get("amplitude_calibrated", False)
    calibration_note = "" if amp_calibrated else "\nNOTE: Amplitude calibration unavailable (grid not detected). ST mV values are relative, not absolute."

    # Build AFib hint if detected
    afib_note = ""
    if measurements.get("afib_hint"):
        afib_note = "\nSIGNAL HINT: Irregularly irregular rhythm with absent P-waves — strongly consider atrial fibrillation."

    # P-wave morphology line
    p_morph = measurements.get("p_wave_morphology")
    p_morph_str = f" ({p_morph})" if p_morph else ""

    # QTc lines — report both formulae when available
    qtcf = measurements.get("qtcf_ms")
    qtc_method = measurements.get("qtc_method", "bazett")
    qtc_line = f"{measurements['qtc_ms']:.0f} ms (Bazett)" if measurements['qtc_ms'] else "not measurable"
    if qtcf is not None:
        qtc_line += f"  |  {qtcf:.0f} ms (Fridericia)"
    qtc_line += f"  [primary: {qtc_method}]"

    return f"""You are an expert cardiologist reviewing an ECG that has been digitized and algorithmically analyzed. The signal measurements below are derived from the actual waveform — treat them as accurate. Do NOT re-estimate these values visually.{calibration_note}{afib_note}{pipeline_hint}

MEASURED SIGNAL DATA (from {digitizer_method}):
- Heart rate: {measurements['heart_rate_bpm']:.0f} bpm
- RR intervals (ms): {rr_str}
- Rhythm regularity: {measurements['regularity']}
- Beats detected: {measurements['num_beats']}
- P waves present: {measurements['p_waves_present']}{p_morph_str}
- PR interval: {f"{measurements['pr_interval_ms']:.0f} ms" if measurements['pr_interval_ms'] else "not measurable"}
- QRS duration: {f"{measurements['qrs_duration_ms']:.0f} ms" if measurements['qrs_duration_ms'] else "not measurable"}
- QRS wide (≥120ms): {measurements['qrs_wide']}
- QT interval: {f"{measurements['qt_ms']:.0f} ms" if measurements['qt_ms'] else "not measurable"}
- QTc: {qtc_line}
- QTc prolonged: {measurements['qtc_prolonged']}

ST SEGMENT (per lead):
{st_summary}

Using these measurements and the ECG image for morphology context (P-wave axis, QRS shape, T-wave polarity, bundle branch patterns), provide your interpretation as valid JSON matching EXACTLY this schema — no markdown, no extra text:

{{
  "rate": {{
    "bpm": <number>,
    "rr_intervals_ms": {json.dumps(rr[:6])},
    "category": "<bradycardia|normal|tachycardia>",
    "method": "signal-derived",
    "confidence": <0.0-1.0>
  }},
  "rhythm": {{
    "regularity": "<regular|regularly_irregular|irregularly_irregular>",
    "confidence": <0.0-1.0>
  }},
  "p_waves": {{
    "present": <true|false>,
    "signal_morphology": "{measurements.get('p_wave_morphology') or 'null'}",
    "morphology": "<description or null>",
    "ratio": "<e.g. '1:1' or null>",
    "confidence": <0.0-1.0>
  }},
  "pr_interval": {{
    "ms": {measurements['pr_interval_ms'] if measurements['pr_interval_ms'] else 'null'},
    "measured_beats": [],
    "normal": <true|false|null>,
    "fixed": <true|false|null>,
    "confidence": <0.0-1.0>
  }},
  "qrs": {{
    "duration_ms": {measurements['qrs_duration_ms'] if measurements['qrs_duration_ms'] else 'null'},
    "measured_beats_ms": [],
    "wide": {str(measurements['qrs_wide']).lower()},
    "morphology": "<description or null>",
    "confidence": <0.0-1.0>
  }},
  "st_segment": {{
    "elevation": <true|false>,
    "depression": <true|false>,
    "details": "<description or null>",
    "confidence": <0.0-1.0>
  }},
  "t_waves": {{
    "morphology": "<upright|inverted|peaked|flat|biphasic or null>",
    "confidence": <0.0-1.0>
  }},
  "qtc": {{
    "ms": {measurements['qtc_ms'] if measurements['qtc_ms'] else 'null'},
    "fridericia_ms": {measurements.get('qtcf_ms') if measurements.get('qtcf_ms') else 'null'},
    "measured_qt_ms": [{measurements['qt_ms'] if measurements['qt_ms'] else 'null'}],
    "prolonged": {str(measurements['qtc_prolonged']).lower() if measurements['qtc_prolonged'] is not None else 'null'},
    "method": "{measurements.get('qtc_method', 'bazett')}",
    "confidence": <0.0-1.0>
  }},
  "primary_rhythm": "<rhythm name>",
  "overall_confidence": <0.0-1.0>,
  "differentials": ["<rhythm>", "<rhythm>"],
  "explanation": "<2-4 sentence educational explanation grounded in the measured values>",
  "image_quality": "<good|fair|poor>",
  "caveats": "<limitations or null>"
}}"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="ECG image analysis pipeline")
    parser.add_argument("--image", required=True, help="Path to ECG image file")
    args = parser.parse_args()

    image_path = args.image
    if not Path(image_path).exists():
        print(json.dumps({"error": f"Image not found: {image_path}"}), file=sys.stderr)
        sys.exit(1)

    try:
        # Step 1: Digitize
        digitized = digitize_image(image_path)

        # Step 2: Analyze signal
        measurements = analyze_signal(
            digitized["signals"],
            digitized["sampling_rate"],
            calibrated=digitized.get("calibrated", False),
        )

        # Step 3a: PhysioNet pipeline pre-classification
        pipeline_classification = run_pipeline_classification(
            digitized["signals"], digitized["sampling_rate"]
        )

        # Step 3b: Build Claude prompt (includes classification hint)
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
