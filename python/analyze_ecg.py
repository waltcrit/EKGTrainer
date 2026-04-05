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
import sys
import traceback
from pathlib import Path
from typing import Any, NotRequired, Protocol, TypeAlias, TypedDict, cast

import numpy as np
import json as _json_module
from numpy.typing import NDArray


SignalArray: TypeAlias = NDArray[np.float64]
SignalMap: TypeAlias = dict[str, SignalArray]


class DigitizedResult(TypedDict):
    signals: SignalMap
    sampling_rate: int
    method: str


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
    pr_interval_ms: float | None
    qrs_duration_ms: float | None
    qrs_wide: bool
    qt_ms: float | None
    qtc_ms: float | None
    qtc_prolonged: bool | None
    st: STResults
    num_beats: int
    rhythm_lead: str
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
except Exception:
    classify_ecg = None
    _arr_display_names: dict[str, str] = {}
    _pipeline_available = False


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

def digitize_image(image_path: str) -> DigitizedResult:
    """
    Convert an ECG image to a digital signal using ECG-Digitiser.
    Returns a dict with keys: signals (dict of lead->np.ndarray), sampling_rate (int).

    Falls back to a simpler OpenCV-based approach if ECG-Digitiser is not installed.
    """
    try:
        digitiser_module = importlib.import_module("ecg_digitiser.digitiser")
        ECGDigitiser = digitiser_module.ECGDigitiser
        digitiser = ECGDigitiser()
        result = digitiser.digitise(image_path)
        # ECG-Digitiser returns a dict of lead name -> signal array and a sampling rate
        signals = {
            str(lead): np.asarray(values, dtype=np.float64)
            for lead, values in cast(dict[object, object], result.signals).items()
        }
        return {
            "signals": signals,
            "sampling_rate": int(result.sampling_rate),
            "method": "ecg-digitiser",
        }
    except ImportError:
        pass

    # Fallback: basic image tracing for single rhythm strip (Lead II assumed)
    return _fallback_digitize(image_path)


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


def _fallback_digitize(image_path: str) -> DigitizedResult:
    """
    Grid-calibrated OpenCV digitizer.

    Detects the ECG paper grid via FFT to determine the true sampling rate,
    then traces the waveform and normalizes the signal for BioSPPy.
    """
    try:
        import cv2
    except ImportError:
        raise RuntimeError(
            "opencv-python is not installed. Cannot digitize ECG image."
        )

    img_bgr = cast(NDArray[np.uint8] | None, cv2.imread(image_path))
    if img_bgr is None:
        raise RuntimeError(f"Could not read image: {image_path}")

    gray = cast(NDArray[np.uint8], cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY))
    h, w = gray.shape

    # ── Step 1: calibrate sampling rate from grid ─────────────────────────
    cal = _detect_grid_calibration(gray)
    if cal:
        sampling_rate = int(round(cal["sampling_rate_hz"]))
        method = f"fallback-opencv-calibrated({sampling_rate}Hz)"
    else:
        sampling_rate = 179   # observed default across our image set
        method = "fallback-opencv-uncalibrated"

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
    scipy_ndimage_pre = importlib.import_module("scipy.ndimage")
    trace_row = scipy_ndimage_pre.median_filter(trace_row, size=3).astype(float)

    # Flip: row 0 is top of image; upward deflections → smaller row index.
    signal = (h - 1) - trace_row

    # ── Step 3: baseline-correct and normalize ────────────────────────────
    # Remove slow baseline wander with a wide median filter, then scale to
    # a physiologically plausible mV range so BioSPPy's thresholds work.
    scipy_ndimage = importlib.import_module("scipy.ndimage")
    median_filter_fn = scipy_ndimage.median_filter
    bl_window = max(3, int(sampling_rate * 0.6) | 1)  # must be odd
    baseline = cast(SignalArray, median_filter_fn(signal, size=bl_window, mode="nearest"))
    signal = signal - baseline

    if signal.std() > 0:
        signal = signal / signal.std() * 0.5   # normalize to ≈ ±0.5 mV std

    # Suppress pacing artifacts: very narrow high-amplitude spikes (≤3 samples).
    # Pacing stimuli appear as 1-2 pixel-wide vertical lines in the image;
    # after tracing they become isolated extreme values that confuse R-peak detectors.
    spike_thr = float(np.percentile(np.abs(signal), 99.5)) * 2.0
    spike_mask = np.abs(signal) > spike_thr
    labeled_spikes, n_spikes = scipy_ndimage_pre.label(spike_mask)
    for spike_id in range(1, n_spikes + 1):
        spike_idx = np.where(labeled_spikes == spike_id)[0]
        if len(spike_idx) <= 3:   # narrow spike = pacing artifact
            lo_i = max(0, spike_idx[0] - 1)
            hi_i = min(len(signal) - 1, spike_idx[-1] + 1)
            signal[spike_idx] = np.interp(
                spike_idx.astype(float),
                [float(lo_i), float(hi_i)],
                [signal[lo_i], signal[hi_i]],
            )

    return {
        "signals":       {"II": signal},
        "sampling_rate": sampling_rate,
        "method":        method,
    }


# ---------------------------------------------------------------------------
# Step 2 — Signal processing with BioSPPy
# ---------------------------------------------------------------------------

def analyze_signal(signals: SignalMap, sampling_rate: int) -> SignalMeasurements:
    """
    Run BioSPPy ECG analysis on the digitized signals.
    Processes Lead II (or the first available lead) for rhythm metrics,
    and runs per-lead ST/T analysis when multiple leads are present.
    """
    bsp_ecg_module = cast(Any, importlib.import_module("biosppy.signals.ecg"))

    # Prefer Lead II for rhythm analysis; fall back to first available
    rhythm_lead_name = "II" if "II" in signals else next(iter(signals))
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
    except Exception:
        # BioSPPy can fail on wide QRS, pacing spikes, or very short signals.
        # Fall back to scipy peak detection with physiologically-guided settings.
        from scipy.signal import find_peaks as _sp_find_peaks  # type: ignore
        min_dist = max(1, int(sampling_rate * 0.25))   # >= 250 ms between beats
        thresh   = float(np.percentile(rhythm_signal, 65))
        peak_idx, _ = _sp_find_peaks(
            rhythm_signal, height=thresh, distance=min_dist
        )
        r_peaks = np.asarray(peak_idx, dtype=np.int64)
        templates_raw = None

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
                rr_intervals_ms = _cv_rr
                heart_rate_bpm = _cv_hr
                regularity = _regularity(_cv_rr)
                break

    # QRS width: measure each template (BioSPPy supplies beat templates)
    templates = np.asarray(templates_raw, dtype=np.float64) if templates_raw is not None else None
    qrs_ms, qrs_wide = _qrs_width(templates, sampling_rate)

    # P-wave / PR interval: simple heuristic from template shape
    pr_ms, p_present = _pr_interval(templates, sampling_rate)

    # QT/QTc
    qt_ms, qtc_ms, qtc_prolonged = _qtc(templates, rr_intervals_ms, sampling_rate)

    # ST segment (per lead if available)
    st_results = _st_analysis(signals, r_peaks, sampling_rate)

    return {
        "r_peaks": r_peaks.tolist(),
        "rr_intervals_ms": [round(x, 1) for x in rr_intervals_ms],
        "heart_rate_bpm": round(heart_rate_bpm, 1),
        "regularity": regularity,
        "p_waves_present": p_present,
        "pr_interval_ms": round(pr_ms, 1) if pr_ms is not None else None,
        "qrs_duration_ms": round(qrs_ms, 1) if qrs_ms is not None else None,
        "qrs_wide": qrs_wide,
        "qt_ms": round(qt_ms, 1) if qt_ms is not None else None,
        "qtc_ms": round(qtc_ms, 1) if qtc_ms is not None else None,
        "qtc_prolonged": qtc_prolonged,
        "st": st_results,
        "num_beats": len(r_peaks),
        "rhythm_lead": rhythm_lead_name,
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


def _qrs_width(templates: NDArray[np.float64] | None, fs: int) -> tuple[float | None, bool]:
    """Estimate QRS duration from beat templates."""
    if templates is None or len(templates) == 0:
        return None, False
    # Use median template
    tmpl = np.median(templates, axis=0)
    # Find energy envelope; QRS is the central high-energy region
    energy = tmpl ** 2
    threshold = energy.max() * 0.1
    above = np.where(energy > threshold)[0]
    if len(above) < 2:
        return None, False
    width_samples = above[-1] - above[0]
    width_ms = width_samples / fs * 1000
    return width_ms, width_ms >= 120


def _pr_interval(templates: NDArray[np.float64] | None, fs: int) -> tuple[float | None, bool]:
    """
    Estimate PR interval and P-wave presence from the BioSPPy template.
    BioSPPy centres templates on the R peak; P wave typically appears
    ~100–200 ms before the R peak (= earlier samples in the template).
    """
    if templates is None or len(templates) == 0:
        return None, False

    tmpl = np.median(templates, axis=0)
    mid = len(tmpl) // 2  # approximate R-peak position in template

    # Look for P-wave deflection in the 50–250 ms window before R peak
    pre_start = max(0, mid - int(0.25 * fs))
    pre_end = max(0, mid - int(0.05 * fs))
    pre_region = tmpl[pre_start:pre_end]

    if len(pre_region) == 0:
        return None, False

    # P-wave present if there is a meaningful positive deflection before R
    peak_amp = np.max(np.abs(pre_region))
    r_amp = np.max(np.abs(tmpl[mid - 5:mid + 5])) if mid >= 5 else np.max(np.abs(tmpl))
    p_present = peak_amp > r_amp * 0.08  # P > 8% of R amplitude

    if not p_present:
        return None, False

    # PR = distance from P-peak to R-peak
    p_peak_idx = pre_start + np.argmax(np.abs(pre_region))
    pr_samples = mid - p_peak_idx
    pr_ms = pr_samples / fs * 1000
    return pr_ms, True


def _qtc(
    templates: NDArray[np.float64] | None,
    rr_ms: list[float],
    fs: int,
) -> tuple[float | None, float | None, bool | None]:
    """Estimate QT interval and Bazett-corrected QTc."""
    if templates is None or len(templates) == 0 or not rr_ms:
        return None, None, None

    tmpl = np.median(templates, axis=0)
    mid = len(tmpl) // 2
    # T-wave end: look for return to baseline after the T wave
    post_start = mid + int(0.05 * fs)
    post_end = min(len(tmpl), mid + int(0.50 * fs))
    post_region = tmpl[post_start:post_end]

    if len(post_region) == 0:
        return None, None, None

    # T-wave offset: last sample > 10% of T-peak amplitude
    t_peak = np.max(np.abs(post_region))
    above = np.where(np.abs(post_region) > t_peak * 0.10)[0]
    if len(above) == 0:
        return None, None, None

    t_end_idx = post_start + above[-1]
    qt_samples = t_end_idx - (mid - int(0.04 * fs))  # from Q onset (approx)
    qt_ms = qt_samples / fs * 1000

    # Bazett: QTc = QT / sqrt(RR in seconds)
    rr_sec = np.mean(rr_ms) / 1000.0
    qtc_ms = qt_ms / np.sqrt(rr_sec) if rr_sec > 0 else None
    prolonged = qtc_ms > 450 if qtc_ms is not None else None

    return qt_ms, qtc_ms, prolonged


def _st_analysis(signals: SignalMap, r_peaks: np.ndarray, fs: int) -> STResults:
    """
    Simple ST segment analysis: measure amplitude ~80 ms after R peak
    across all available leads.
    """
    offset_samples = int(0.08 * fs)  # J+80 ms
    results: STResults = {}

    for lead, sig in signals.items():
        if len(r_peaks) == 0:
            results[lead] = {"elevation": False, "depression": False, "mean_mv": 0.0}
            continue
        measurements: list[float] = []
        for rp in r_peaks:
            idx = rp + offset_samples
            if idx < len(sig):
                measurements.append(float(sig[idx]))
        if not measurements:
            continue
        mean_st = float(np.mean(measurements))
        results[lead] = {
            "elevation": mean_st > 0.1,      # >1 mm above baseline
            "depression": mean_st < -0.05,   # >0.5 mm below baseline
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
    except Exception as exc:
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

    return f"""You are an expert cardiologist reviewing an ECG that has been digitized and algorithmically analyzed. The signal measurements below are derived from the actual waveform — treat them as accurate. Do NOT re-estimate these values visually.{pipeline_hint}

MEASURED SIGNAL DATA (from {digitizer_method}):
- Heart rate: {measurements['heart_rate_bpm']:.0f} bpm
- RR intervals (ms): {rr_str}
- Rhythm regularity: {measurements['regularity']}
- Beats detected: {measurements['num_beats']}
- P waves present: {measurements['p_waves_present']}
- PR interval: {f"{measurements['pr_interval_ms']:.0f} ms" if measurements['pr_interval_ms'] else "not measurable"}
- QRS duration: {f"{measurements['qrs_duration_ms']:.0f} ms" if measurements['qrs_duration_ms'] else "not measurable"}
- QRS wide (≥120ms): {measurements['qrs_wide']}
- QT interval: {f"{measurements['qt_ms']:.0f} ms" if measurements['qt_ms'] else "not measurable"}
- QTc (Bazett): {f"{measurements['qtc_ms']:.0f} ms" if measurements['qtc_ms'] else "not measurable"}
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
    "measured_qt_ms": [{measurements['qt_ms'] if measurements['qt_ms'] else 'null'}],
    "prolonged": {str(measurements['qtc_prolonged']).lower() if measurements['qtc_prolonged'] is not None else 'null'},
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
        measurements = analyze_signal(digitized["signals"], digitized["sampling_rate"])

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
