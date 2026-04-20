"""ECG signal measurement: R-peak detection, HR, intervals, ST analysis."""
from __future__ import annotations

import logging
from typing import cast

import numpy as np
from numpy.typing import NDArray

from ecg.types import SignalArray, SignalMap, SignalMeasurements, STLeadResult, STResults

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hoisted optional imports
# ---------------------------------------------------------------------------
try:
    import biosppy.signals.ecg as bsp_ecg_module
    _biosppy_available = True
except ImportError:
    _biosppy_available = False


def analyze_signal(
    signals: SignalMap,
    sampling_rate: int,
    calibrated: bool = False,
) -> SignalMeasurements:
    """
    Run BioSPPy ECG analysis on digitized signals.
    Picks rhythm lead by RMS amplitude; computes HR, intervals, QRS/PR/QT/ST.
    """
    if not _biosppy_available:
        raise RuntimeError("biosppy is not installed. Cannot analyze ECG signal.")

    def _lead_rms(sig: SignalArray) -> float:
        return float(np.sqrt(np.mean(sig ** 2)))

    rhythm_lead_name = max(
        signals,
        key=lambda lead: _lead_rms(signals[lead]) * (1.05 if lead == "II" else 1.0),
    )
    rhythm_signal = signals[rhythm_lead_name]

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
        min_dist = max(1, int(sampling_rate * 0.25))
        thresh   = float(np.percentile(rhythm_signal, 65))
        peak_idx, _ = _sp_find_peaks(rhythm_signal, height=thresh, distance=min_dist)
        r_peaks = np.asarray(peak_idx, dtype=np.int64)
        templates_raw = None

    r_peaks = _clean_r_peaks(r_peaks, rhythm_signal, sampling_rate)

    rr_intervals_ms = _rr_intervals(r_peaks, sampling_rate)
    heart_rate_bpm = _mean_hr(rr_intervals_ms)
    regularity = _regularity(rr_intervals_ms)

    # Sanity check: if HR is implausible, retry with higher thresholds
    _implausible = (
        heart_rate_bpm > 280
        or heart_rate_bpm < 20
        or (len(r_peaks) < 3 and len(rhythm_signal) > sampling_rate * 5)
    )
    if _implausible:
        from scipy.signal import find_peaks as _sp_cv  # type: ignore
        cv_dist = max(1, int(sampling_rate * 0.27))
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

    templates = np.asarray(templates_raw, dtype=np.float64) if templates_raw is not None else None
    median_template = np.median(templates, axis=0) if templates is not None and len(templates) > 0 else None

    qrs_ms, qrs_wide = _qrs_width(median_template, sampling_rate)
    j_offset = _detect_j_point(median_template, sampling_rate)
    pr_ms, p_present, p_morphology = _pr_interval(median_template, sampling_rate, calibrated)
    p_peaks, pp_intervals_ms = _detect_p_peaks(rhythm_signal, r_peaks, median_template, sampling_rate)
    qt_ms, qtc_ms, qtcf_ms, qtc_prolonged, qtc_method = _qtc(
        median_template, rr_intervals_ms, sampling_rate, heart_rate_bpm
    )
    r_amp = float(median_template[len(median_template) // 2]) if median_template is not None else None
    st_results = _st_analysis(signals, r_peaks, sampling_rate, j_offset, calibrated=calibrated, r_amplitude=r_amp)

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
        "p_peaks": [int(p) for p in p_peaks],
        "pp_intervals_ms": pp_intervals_ms,
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
    valid = arr[(arr > median_rr * 0.40) & (arr < median_rr * 2.50)]
    if len(valid) < 2:
        valid = arr

    cluster_ratio = float(np.mean(np.abs(valid - median_rr) <= median_rr * 0.12))
    if cluster_ratio >= 0.72:
        return "regular"

    mean_v = float(np.mean(valid))
    cv = float(np.std(valid) / mean_v) if mean_v > 0 else 1.0
    if cv < 0.08:
        return "regular"
    diffs = np.diff(valid)
    if len(diffs) >= 2 and float(np.std(diffs)) < float(np.std(valid)) * 0.55:
        return "regularly_irregular"
    return "irregularly_irregular"


def _detect_j_point(median_template: NDArray[np.float64] | None, fs: int) -> int:
    """
    Estimate J-point offset (in samples) from R-peak.
    Energy-based: walk forward until energy drops below 15% of R-peak.
    Returns default 40 ms if detection fails.
    """
    default = max(1, int(0.04 * fs))
    if median_template is None or len(median_template) == 0:
        return default

    mid = len(median_template) // 2
    search_end = min(len(median_template), mid + int(0.12 * fs))
    post_r = median_template[mid:search_end]

    if len(post_r) == 0:
        return default

    r_energy = float(median_template[mid] ** 2)
    if r_energy == 0:
        return default

    energy = post_r ** 2
    below = np.where(energy < r_energy * 0.15)[0]
    if len(below) == 0:
        return default

    j_offset = int(below[0])
    return max(int(0.02 * fs), min(j_offset, int(0.10 * fs)))


def _qrs_width(median_template: NDArray[np.float64] | None, fs: int) -> tuple[float | None, bool]:
    """
    Estimate QRS duration from median template.
    Constrains to ±80 ms window around R-peak to exclude T-wave.
    """
    if median_template is None or len(median_template) == 0:
        return None, False
    mid = len(median_template) // 2
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
    Estimate PR interval and P-wave presence/morphology.
    Detects polarity: "upright" | "inverted" | "biphasic".
    Uses absolute 0.1 mV threshold when calibrated; 10% of R otherwise.
    """
    if median_template is None or len(median_template) == 0:
        return None, False, None

    tmpl = median_template
    mid = len(tmpl) // 2
    pre_start = max(0, mid - int(0.25 * fs))
    pre_end = max(0, mid - int(0.05 * fs))
    pre_region = tmpl[pre_start:pre_end]

    if len(pre_region) == 0:
        return None, False, None

    r_amp = float(np.max(np.abs(tmpl[max(0, mid - 5):mid + 5]))) if mid >= 5 else float(np.max(np.abs(tmpl)))
    threshold = 0.10 if (calibrated and r_amp > 0.10) else r_amp * 0.10

    pos_peak = float(np.max(pre_region))
    neg_peak = float(np.min(pre_region))

    has_pos = pos_peak > threshold
    has_neg = abs(neg_peak) > threshold

    if not has_pos and not has_neg:
        return None, False, None

    if has_pos and has_neg:
        morphology = "biphasic"
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


def _p_polarity(
    median_template: NDArray[np.float64] | None,
    fs: int,
) -> str:
    """
    Return "upright" or "inverted" P-wave polarity from the median template.
    Falls back to "upright" when no P-wave is detectable.
    """
    if median_template is None or len(median_template) == 0:
        return "upright"
    mid = len(median_template) // 2
    pre_start = max(0, mid - int(0.25 * fs))
    pre_end = max(0, mid - int(0.05 * fs))
    pre_region = median_template[pre_start:pre_end]
    if len(pre_region) == 0:
        return "upright"
    r_amp = float(np.max(np.abs(median_template[max(0, mid - 5):mid + 5]))) if mid >= 5 else 1.0
    threshold = r_amp * 0.08
    pos_peak = float(np.max(pre_region))
    neg_peak = float(np.min(pre_region))
    if abs(neg_peak) > pos_peak and abs(neg_peak) > threshold:
        return "inverted"
    return "upright"


def _detect_p_peaks(
    signal: NDArray[np.float64],
    r_peaks: np.ndarray,
    median_template: NDArray[np.float64] | None,
    fs: int,
) -> tuple[list[int], list[float]]:
    """
    Detect P-wave peak positions in the raw signal and compute P-P intervals.

    Two-pass approach:
      1. Anchored: search the PR window before each R-peak (one P per QRS).
      2. Mid-RR: for long R-R intervals (>700 ms) search the post-T / pre-P
         segment for dissociated P-waves — the signature of high-degree AV block.

    Returns:
        p_peaks:         sorted absolute sample indices of detected P-peaks
        pp_intervals_ms: successive P-P intervals in ms
    """
    if len(r_peaks) < 2:
        return [], []

    polarity = _p_polarity(median_template, fs)
    r_amp = float(np.median(np.abs(signal[r_peaks]))) if len(r_peaks) > 0 else 1.0
    min_amp = r_amp * 0.07  # 7% of median R amplitude

    def _peak_in_window(win: NDArray[np.float64]) -> tuple[int, float]:
        if polarity == "inverted":
            idx = int(np.argmin(win))
            return idx, abs(float(win[idx]))
        idx = int(np.argmax(win))
        return idx, float(win[idx])

    # Pass 1 — anchored to each R-peak
    anchored: list[int] = []
    pre_start_samples = int(0.26 * fs)
    pre_end_samples = int(0.05 * fs)
    for rp in r_peaks:
        ws = max(0, rp - pre_start_samples)
        we = max(0, rp - pre_end_samples)
        if we <= ws:
            continue
        window = signal[ws:we]
        idx, amp = _peak_in_window(window)
        if amp >= min_amp:
            anchored.append(ws + idx)

    # Pass 2 — mid-RR search for dissociated P-waves (>700 ms R-R gap)
    extra: list[int] = []
    rr_samples = np.diff(r_peaks)
    for i, rr in enumerate(rr_samples):
        rr_ms = rr / fs * 1000
        if rr_ms < 700:
            continue
        # Blank past the T-wave (~250 ms after R) and stop 150 ms before next R
        seg_start = r_peaks[i] + int(0.25 * fs)
        seg_end = r_peaks[i + 1] - int(0.15 * fs)
        if seg_end <= seg_start or seg_start < 0 or seg_end > len(signal):
            continue
        segment = signal[seg_start:seg_end]
        if len(segment) < int(0.05 * fs):
            continue
        idx, amp = _peak_in_window(segment)
        if amp >= min_amp:
            extra.append(seg_start + idx)

    # Merge, sort, deduplicate (min 150 ms separation)
    all_peaks = sorted(set(anchored + extra))
    min_sep = int(0.15 * fs)
    deduped: list[int] = []
    for pk in all_peaks:
        if not deduped or pk - deduped[-1] >= min_sep:
            deduped.append(pk)

    pp_intervals: list[float] = [
        round((deduped[j + 1] - deduped[j]) / fs * 1000, 1)
        for j in range(len(deduped) - 1)
    ]
    return deduped, pp_intervals


def _qtc(
    median_template: NDArray[np.float64] | None,
    rr_ms: list[float],
    fs: int,
    heart_rate_bpm: float = 75.0,
) -> tuple[float | None, float | None, float | None, bool | None, str]:
    """
    Estimate QT and rate-corrected QTc (Bazett + Fridericia).
    Q-onset is energy-based (not fixed 40 ms).
    Selects formula for prolonged flag: Bazett (60–100 bpm), Fridericia (extremes).
    """
    if median_template is None or len(median_template) == 0 or not rr_ms:
        return None, None, None, None, "bazett"

    tmpl = median_template
    mid = len(tmpl) // 2

    pre_r_start = max(0, mid - int(0.10 * fs))
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

    rr_sec = float(np.mean(rr_ms)) / 1000.0
    if rr_sec <= 0:
        return qt_ms, None, None, None, "bazett"

    qtc_bazett = qt_ms / (rr_sec ** 0.5)
    qtc_fridericia = qt_ms / (rr_sec ** (1.0 / 3.0))

    if heart_rate_bpm > 100 or heart_rate_bpm < 60:
        qtc_primary = qtc_fridericia
        method = "fridericia"
    else:
        qtc_primary = qtc_bazett
        method = "bazett"

    prolonged = qtc_primary > 450

    return qt_ms, qtc_bazett, qtc_fridericia, prolonged, method


_ST_ELEVATION_THRESHOLDS: dict[str, float] = {
    "V2": 0.20,
    "V3": 0.20,
}
_ST_ELEVATION_DEFAULT = 0.10
_ST_DEPRESSION_THRESHOLD = 0.05


def _st_analysis(
    signals: SignalMap,
    r_peaks: np.ndarray,
    fs: int,
    j_offset_samples: int = 0,
    calibrated: bool = False,
    r_amplitude: float | None = None,
) -> STResults:
    """
    ST segment analysis across all leads.
    Measures at J-point + 80 ms using PR-segment baseline (50–20 ms before R).
    Applies AHA lead-specific elevation thresholds when calibrated.
    Falls back to relative thresholds (10% / 5% of R amplitude) when uncalibrated,
    since normalization removes the absolute mV scale.
    """
    st_offset = j_offset_samples + int(0.08 * fs)
    pr_start = int(0.05 * fs)
    pr_end = int(0.02 * fs)
    results: STResults = {}

    for lead, sig in signals.items():
        if len(r_peaks) == 0:
            results[lead] = {"elevation": False, "depression": False, "mean_mv": 0.0}
            continue

        r_amps: list[float] = []
        st_vals: list[float] = []
        for rp in r_peaks:
            st_idx = rp + st_offset
            if st_idx >= len(sig):
                continue
            bl_start = max(0, rp - pr_start)
            bl_end = max(0, rp - pr_end)
            baseline = float(np.mean(sig[bl_start:bl_end])) if bl_end > bl_start else 0.0
            st_vals.append(float(sig[st_idx]) - baseline)
            r_amps.append(abs(float(sig[rp])))

        if not st_vals:
            continue

        mean_st = float(np.mean(st_vals))

        if calibrated:
            elev_thresh = _ST_ELEVATION_THRESHOLDS.get(lead, _ST_ELEVATION_DEFAULT)
            dep_thresh = _ST_DEPRESSION_THRESHOLD
        else:
            # Relative thresholds: 10% of R for elevation, 5% for depression.
            # Uses per-beat R amplitudes when available, else the passed r_amplitude.
            ref_amp = float(np.mean(r_amps)) if r_amps else (r_amplitude or 1.0)
            elev_thresh = ref_amp * 0.10
            dep_thresh = ref_amp * 0.05

        results[lead] = {
            "elevation": mean_st > elev_thresh,
            "depression": mean_st < -dep_thresh,
            "mean_mv": round(mean_st, 3),
        }

    return results
