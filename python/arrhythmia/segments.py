"""
ECG segmentation: beat windows and rhythm strip windows.

Public API
----------
extract_beat_windows(signal, r_peaks, fs, pre_ms, post_ms)
    -> list[np.ndarray]   — one window per beat

extract_rhythm_windows(signal, fs, window_s, step_s)
    -> list[np.ndarray]   — overlapping or non-overlapping rhythm strips

pad_or_truncate(window, target_len)
    -> np.ndarray         — fixed-length window for model input
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Beat-level segmentation
# ---------------------------------------------------------------------------

def extract_beat_windows(
    signal: np.ndarray,
    r_peaks: np.ndarray,
    fs: int,
    pre_ms: float = 200.0,
    post_ms: float = 400.0,
    pad_value: float = 0.0,
) -> list[np.ndarray]:
    """
    Extract fixed-length windows centred on each R-peak.

    Default window (200 ms pre, 400 ms post) captures:
      - P wave and PR segment (pre-R)
      - QRS complex + ST segment + T wave (post-R)

    Parameters
    ----------
    signal    : 1-D float64 ECG signal
    r_peaks   : int64 array of R-peak sample indices
    fs        : sampling frequency (Hz)
    pre_ms    : milliseconds before R-peak to include (default 200)
    post_ms   : milliseconds after R-peak to include (default 400)
    pad_value : value used for boundary padding (default 0.0)

    Returns
    -------
    windows : list of 1-D float64 arrays, each of length pre_samples + post_samples
    """
    signal = np.asarray(signal, dtype=np.float64)
    pre_samples = int(round(pre_ms * fs / 1000.0))
    post_samples = int(round(post_ms * fs / 1000.0))
    window_len = pre_samples + post_samples
    n = len(signal)

    windows: list[np.ndarray] = []
    for peak in r_peaks:
        peak = int(peak)
        start = peak - pre_samples
        end = peak + post_samples

        if start < 0 or end > n:
            # Pad with pad_value at boundaries
            window = np.full(window_len, pad_value, dtype=np.float64)
            src_start = max(0, start)
            src_end = min(n, end)
            dst_start = src_start - start
            dst_end = dst_start + (src_end - src_start)
            window[dst_start:dst_end] = signal[src_start:src_end]
        else:
            window = signal[start:end].copy()

        windows.append(window)

    return windows


# ---------------------------------------------------------------------------
# Rhythm-level segmentation
# ---------------------------------------------------------------------------

def extract_rhythm_windows(
    signal: np.ndarray,
    fs: int,
    window_s: float = 10.0,
    step_s: float | None = None,
    pad_value: float = 0.0,
) -> list[np.ndarray]:
    """
    Extract rhythm strip windows from a continuous ECG signal.

    Used for strip-level classification (AF, AFL, SVT, VT, VF, Asystole).

    Parameters
    ----------
    signal   : 1-D float64 ECG signal
    fs       : sampling frequency (Hz)
    window_s : window duration in seconds (default 10.0)
    step_s   : step between window starts in seconds;
               None = non-overlapping (step == window)
    pad_value: value used to pad the final window if shorter

    Returns
    -------
    windows : list of 1-D float64 arrays, each of length window_samples
    """
    signal = np.asarray(signal, dtype=np.float64)
    window_samples = int(round(window_s * fs))
    step_samples = window_samples if step_s is None else int(round(step_s * fs))
    n = len(signal)

    windows: list[np.ndarray] = []
    start = 0
    while start < n:
        end = start + window_samples
        chunk = signal[start:min(end, n)]
        if len(chunk) < window_samples:
            # Pad last window
            padded = np.full(window_samples, pad_value, dtype=np.float64)
            padded[:len(chunk)] = chunk
            windows.append(padded)
        else:
            windows.append(chunk.copy())
        start += step_samples

    return windows


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def pad_or_truncate(
    window: np.ndarray,
    target_len: int,
    pad_value: float = 0.0,
) -> np.ndarray:
    """
    Ensure a window has exactly target_len samples.

    Pads with pad_value on the right if shorter; truncates on the right
    if longer.

    Parameters
    ----------
    window     : 1-D float64 array
    target_len : desired number of samples
    pad_value  : padding fill value (default 0.0)

    Returns
    -------
    fixed : 1-D float64 array of length target_len
    """
    window = np.asarray(window, dtype=np.float64)
    n = len(window)
    if n == target_len:
        return window.copy()
    elif n < target_len:
        padded = np.full(target_len, pad_value, dtype=np.float64)
        padded[:n] = window
        return padded
    else:
        return window[:target_len].copy()
