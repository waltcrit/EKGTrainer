"""
Feature extraction for ECG arrhythmia classification.

Two feature sets
----------------
1. Classical features — from RR intervals and signal morphology.
   Used by lightweight classifiers and as inputs to deep models.

2. Wavelet / frequency features — DWT-based energy descriptors.
   Requires PyWavelets (pip install PyWavelets).

Public API
----------
extract_rr_features(rr_ms)
    -> dict[str, float]

extract_morphology_features(beat_window, fs)
    -> dict[str, float]

extract_wavelet_features(beat_window, wavelet, level)
    -> dict[str, float]   — raises ImportError if PyWavelets missing

extract_beat_features(beat_window, rr_ms, fs)
    -> dict[str, float]   — combined classical + wavelet (if available)

extract_strip_features(rhythm_window, r_peaks_in_window, fs)
    -> dict[str, float]   — strip-level features for rhythm classification
"""

from __future__ import annotations

import importlib
from typing import Any, cast

import numpy as np

# ---------------------------------------------------------------------------
# Wavelet availability
# ---------------------------------------------------------------------------
try:
    pywt = importlib.import_module("pywt")
    _pywt_available = True
except ImportError:
    pywt = None
    _pywt_available = False


# ---------------------------------------------------------------------------
# RR-interval features
# ---------------------------------------------------------------------------

def extract_rr_features(rr_ms: np.ndarray) -> dict[str, float]:
    """
    Compute classical HRV / RR interval features.

    Parameters
    ----------
    rr_ms : 1-D float64 array of RR intervals in milliseconds (≥ 1 element)

    Returns
    -------
    dict with keys:
      rr_mean_ms, rr_std_ms, rr_cv, rr_min_ms, rr_max_ms,
      rr_range_ms, rr_rmssd, rr_nn50, rr_pnn50,
      heart_rate_bpm, heart_rate_std
    """
    rr = np.asarray(rr_ms, dtype=np.float64)
    out: dict[str, float] = {}

    if len(rr) == 0:
        nulls = [
            "rr_mean_ms", "rr_std_ms", "rr_cv", "rr_min_ms", "rr_max_ms",
            "rr_range_ms", "rr_rmssd", "rr_nn50", "rr_pnn50",
            "heart_rate_bpm", "heart_rate_std",
        ]
        return {k: float("nan") for k in nulls}

    out["rr_mean_ms"] = float(np.mean(rr))
    out["rr_std_ms"]  = float(np.std(rr, ddof=1)) if len(rr) > 1 else 0.0
    out["rr_cv"]      = out["rr_std_ms"] / out["rr_mean_ms"] if out["rr_mean_ms"] > 0 else 0.0
    out["rr_min_ms"]  = float(np.min(rr))
    out["rr_max_ms"]  = float(np.max(rr))
    out["rr_range_ms"]= out["rr_max_ms"] - out["rr_min_ms"]

    # RMSSD (root mean square of successive differences)
    if len(rr) > 1:
        diffs = np.diff(rr)
        out["rr_rmssd"] = float(np.sqrt(np.mean(diffs ** 2)))
        out["rr_nn50"]  = float(np.sum(np.abs(diffs) > 50.0))
        out["rr_pnn50"] = float(out["rr_nn50"] / len(diffs))
    else:
        out["rr_rmssd"] = 0.0
        out["rr_nn50"]  = 0.0
        out["rr_pnn50"] = 0.0

    # Instantaneous heart rate
    hr = 60_000.0 / rr
    out["heart_rate_bpm"]  = float(np.mean(hr))
    out["heart_rate_std"]  = float(np.std(hr, ddof=1)) if len(hr) > 1 else 0.0

    return out


# ---------------------------------------------------------------------------
# Morphology features (from a single beat window)
# ---------------------------------------------------------------------------

def extract_morphology_features(
    beat_window: np.ndarray,
    fs: int,
) -> dict[str, float]:
    """
    Compute morphological features from a single beat window.

    Assumes the beat window is centred on the R-peak (i.e. the maximum
    amplitude sample is approximately at the window midpoint after filtering).

    Parameters
    ----------
    beat_window : 1-D float64 array (single beat, preprocessed)
    fs          : sampling frequency (Hz)

    Returns
    -------
    dict with keys:
      r_amplitude, qrs_duration_ms, qrs_energy,
      t_wave_amplitude, st_level_mv,
      skewness, kurtosis, zero_crossings
    """
    w = np.asarray(beat_window, dtype=np.float64)
    out: dict[str, float] = {}

    if len(w) == 0:
        return {k: float("nan") for k in [
            "r_amplitude", "qrs_duration_ms", "qrs_energy",
            "t_wave_amplitude", "st_level_mv",
            "skewness", "kurtosis", "zero_crossings",
        ]}

    out["r_amplitude"] = float(np.max(np.abs(w)))

    # QRS width: contiguous region around the peak where |amplitude| > 50% max
    r_idx = int(np.argmax(np.abs(w)))
    half_max = 0.5 * out["r_amplitude"]
    above = np.abs(w) >= half_max
    # Walk left and right from R-peak
    left = r_idx
    while left > 0 and above[left - 1]:
        left -= 1
    right = r_idx
    while right < len(w) - 1 and above[right + 1]:
        right += 1
    out["qrs_duration_ms"] = float((right - left) / fs * 1000.0)
    out["qrs_energy"]      = float(np.sum(w[left:right + 1] ** 2))

    # T-wave region: 150–350 ms post-R (very rough)
    t_start = r_idx + int(0.15 * fs)
    t_end   = r_idx + int(0.35 * fs)
    t_region = w[t_start:t_end] if t_end <= len(w) else w[t_start:]
    out["t_wave_amplitude"] = float(np.max(np.abs(t_region))) if len(t_region) > 0 else 0.0

    # ST level: mean of signal 80 ms after QRS end
    st_start = right + int(0.08 * fs)
    st_end   = st_start + int(0.04 * fs)
    st_region = w[st_start:st_end] if st_end <= len(w) else w[st_start:]
    out["st_level_mv"] = float(np.mean(st_region)) if len(st_region) > 0 else 0.0

    # Statistical
    from scipy.stats import skew, kurtosis  # type: ignore
    out["skewness"]       = float(skew(w))
    out["kurtosis"]       = float(kurtosis(w))
    out["zero_crossings"] = float(np.sum(np.diff(np.sign(w)) != 0))

    return out


# ---------------------------------------------------------------------------
# Wavelet / frequency features
# ---------------------------------------------------------------------------

def extract_wavelet_features(
    beat_window: np.ndarray,
    wavelet: str = "db4",
    level: int = 4,
) -> dict[str, float]:
    """
    Compute discrete wavelet transform (DWT) energy features.

    Requires PyWavelets: pip install PyWavelets

    Parameters
    ----------
    beat_window : 1-D float64 array (single beat)
    wavelet     : PyWavelets wavelet name (default 'db4')
    level       : decomposition level (default 4)

    Returns
    -------
    dict with keys: dwt_energy_cA{level}, dwt_energy_cD{1..level},
                    dwt_ratio_cD1_cA (high/low energy ratio)

    Raises
    ------
    ImportError if PyWavelets is not installed
    """
    if not _pywt_available:
        raise ImportError(
            "PyWavelets is required for wavelet features. "
            "Install with: pip install PyWavelets"
        )
    assert pywt is not None

    w = np.asarray(beat_window, dtype=np.float64)
    coeffs = cast(list[np.ndarray], cast(Any, pywt).wavedec(w, wavelet=wavelet, level=level))
    # coeffs = [cA_n, cD_n, cD_{n-1}, ..., cD_1]
    out: dict[str, float] = {}

    approx_energy = float(np.sum(coeffs[0] ** 2))
    out[f"dwt_energy_cA{level}"] = approx_energy

    detail_energies: list[float] = []
    for i, cD in enumerate(coeffs[1:], start=1):
        e = float(np.sum(cD ** 2))
        out[f"dwt_energy_cD{level + 1 - i}"] = e
        detail_energies.append(e)

    out["dwt_ratio_cD1_cA"] = (
        detail_energies[-1] / approx_energy if approx_energy > 0 else 0.0
    )
    return out


# ---------------------------------------------------------------------------
# Combined feature extraction
# ---------------------------------------------------------------------------

def extract_beat_features(
    beat_window: np.ndarray,
    rr_ms: np.ndarray,
    fs: int,
    include_wavelet: bool = True,
) -> dict[str, float]:
    """
    Combined beat-level feature vector.

    Merges RR features, morphology features, and (optionally) wavelet features.

    Parameters
    ----------
    beat_window     : 1-D float64 array (single beat window, pre-R centred)
    rr_ms           : RR intervals surrounding this beat (used for context)
    fs              : sampling frequency (Hz)
    include_wavelet : include DWT features if PyWavelets is available

    Returns
    -------
    merged feature dict
    """
    feats: dict[str, float] = {}
    feats.update(extract_rr_features(rr_ms))
    feats.update(extract_morphology_features(beat_window, fs))
    if include_wavelet and _pywt_available:
        feats.update(extract_wavelet_features(beat_window))
    return feats


def extract_strip_features(
    rhythm_window: np.ndarray,
    r_peaks_in_window: np.ndarray,
    fs: int,
) -> dict[str, float]:
    """
    Strip-level feature vector for rhythm classification.

    Parameters
    ----------
    rhythm_window       : 1-D float64 array (10-second ECG strip, preprocessed)
    r_peaks_in_window   : int64 array of R-peak indices within this window
    fs                  : sampling frequency (Hz)

    Returns
    -------
    Feature dict including:
      - RR-interval features (mean, std, rmssd, pnn50, etc.)
      - Ventricular rate and regularity estimates
      - Signal power / baseline flatness
    """
    from scipy.stats import kurtosis  # type: ignore

    w = np.asarray(rhythm_window, dtype=np.float64)
    feats: dict[str, float] = {}

    # RR-based
    if len(r_peaks_in_window) >= 2:
        rr_ms = (np.diff(np.sort(r_peaks_in_window)).astype(np.float64) / fs) * 1000.0
        feats.update(extract_rr_features(rr_ms))
        feats["num_beats"] = float(len(r_peaks_in_window))
    else:
        feats.update({k: float("nan") for k in [
            "rr_mean_ms", "rr_std_ms", "rr_cv", "rr_min_ms", "rr_max_ms",
            "rr_range_ms", "rr_rmssd", "rr_nn50", "rr_pnn50",
            "heart_rate_bpm", "heart_rate_std",
        ]})
        feats["num_beats"] = float(len(r_peaks_in_window))

    # Signal-level features
    feats["signal_power"]     = float(np.mean(w ** 2))
    feats["signal_max_abs"]   = float(np.max(np.abs(w))) if len(w) > 0 else 0.0
    feats["baseline_flatness"]= float(1.0 / (np.std(w) + 1e-6))
    feats["kurtosis"]         = float(kurtosis(w)) if len(w) > 1 else 0.0

    return feats
