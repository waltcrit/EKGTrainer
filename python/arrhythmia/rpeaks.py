"""
R-peak detection and RR interval computation.

Public API
----------
detect_rpeaks(signal, fs, method)
    -> r_peaks: np.ndarray of sample indices

compute_rr_intervals(r_peaks, fs)
    -> rr_ms: np.ndarray of RR intervals in milliseconds

detect_and_compute(signal, fs, method)
    -> (r_peaks, rr_ms)

Supported methods
-----------------
"hamilton"   : Hamilton-Tompkins (via BioSPPy — always available)
"pantompkins" : Pan-Tompkins re-implementation via scipy
"wfdb"       : GQRS detector from wfdb library (requires wfdb)
"""

from __future__ import annotations

import importlib
from typing import Any, cast

from typing import Literal

import numpy as np

DetectionMethod = Literal["hamilton", "pantompkins", "wfdb"]
DEFAULT_METHOD: DetectionMethod = "hamilton"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_hamilton(signal: np.ndarray, fs: int) -> np.ndarray:
    """Use BioSPPy's ecg module (Hamilton-Tompkins)."""
    try:
        bsp_ecg = cast(Any, importlib.import_module("biosppy.signals.ecg"))
        out = cast(dict[str, object], bsp_ecg.ecg(signal=signal, sampling_rate=fs, show=False))
        return np.asarray(out["rpeaks"], dtype=np.int64)
    except Exception as exc:
        raise RuntimeError(f"BioSPPy R-peak detection failed: {exc}") from exc


def _detect_pantompkins(signal: np.ndarray, fs: int) -> np.ndarray:
    """
    Simplified Pan-Tompkins detector implemented with scipy.

    Steps:
      1. Differentiate
      2. Square
      3. Moving-window integration
      4. Threshold + peak search
    """
    sig = np.asarray(signal, dtype=np.float64)
    # Derivative
    diff = np.diff(sig, prepend=sig[0])
    # Square
    squared = diff ** 2
    # Moving-window integration (150 ms window)
    win = max(1, int(0.15 * fs))
    kernel = np.ones(win) / win
    integrated = np.convolve(squared, kernel, mode="same")

    # Adaptive threshold: 50% of max
    threshold = 0.5 * np.max(integrated)
    # Minimum distance between peaks: 200 ms refractory
    min_dist = int(0.20 * fs)

    scipy_signal = cast(Any, importlib.import_module("scipy.signal"))
    peaks, _ = scipy_signal.find_peaks(integrated, height=threshold, distance=min_dist)
    return peaks.astype(np.int64)


def _detect_wfdb(signal: np.ndarray, fs: int) -> np.ndarray:
    """Use WFDB's GQRS detector."""
    try:
        wfdb_proc = cast(Any, importlib.import_module("wfdb.processing"))
    except ImportError:
        raise ImportError(
            "wfdb is required for the 'wfdb' detection method. "
            "Install with: pip install wfdb"
        )
    sig = signal.astype(np.float64)
    qrs = wfdb_proc.gqrs_detect(sig=sig, fs=fs)
    return np.asarray(qrs, dtype=np.int64)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_rpeaks(
    signal: np.ndarray,
    fs: int,
    method: DetectionMethod = DEFAULT_METHOD,
) -> np.ndarray:
    """
    Detect R-peaks in an ECG signal.

    Parameters
    ----------
    signal : 1-D float64 ECG (preprocessed)
    fs     : sampling frequency (Hz)
    method : detection algorithm ('hamilton', 'pantompkins', 'wfdb')

    Returns
    -------
    r_peaks : int64 array of sample indices of detected R-peaks
    """
    signal = np.asarray(signal, dtype=np.float64)
    if len(signal) == 0:
        return np.array([], dtype=np.int64)

    if method == "hamilton":
        return _detect_hamilton(signal, fs)
    elif method == "pantompkins":
        return _detect_pantompkins(signal, fs)
    elif method == "wfdb":
        return _detect_wfdb(signal, fs)
    else:
        raise ValueError(f"Unknown detection method: '{method}'. "
                         f"Choose from: hamilton, pantompkins, wfdb")


def compute_rr_intervals(
    r_peaks: np.ndarray,
    fs: int,
) -> np.ndarray:
    """
    Compute RR intervals in milliseconds from R-peak sample indices.

    Parameters
    ----------
    r_peaks : int64 array of R-peak sample indices (sorted, ascending)
    fs      : sampling frequency (Hz)

    Returns
    -------
    rr_ms : float64 array of len(r_peaks) - 1 RR intervals in ms
    """
    if len(r_peaks) < 2:
        return np.array([], dtype=np.float64)
    r_peaks = np.sort(np.asarray(r_peaks, dtype=np.float64))
    rr_samples = np.diff(r_peaks)
    return (rr_samples / fs) * 1000.0


def detect_and_compute(
    signal: np.ndarray,
    fs: int,
    method: DetectionMethod = DEFAULT_METHOD,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Convenience wrapper: detect R-peaks and return (r_peaks, rr_ms).

    Returns
    -------
    r_peaks : int64 array of R-peak sample indices
    rr_ms   : float64 array of RR intervals in milliseconds
    """
    r_peaks = detect_rpeaks(signal, fs, method=method)
    rr_ms = compute_rr_intervals(r_peaks, fs)
    return r_peaks, rr_ms
