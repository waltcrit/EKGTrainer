"""
ECG signal preprocessing.

Public API
----------
bandpass_filter(signal, fs, lowcut, highcut, order)
    -> filtered signal

remove_baseline_wander(signal, fs, cutoff, order)
    -> baseline-corrected signal

resample_signal(signal, fs_in, fs_out)
    -> (resampled_signal, fs_out)

preprocess(signal, fs, target_fs, bp_low, bp_high, bp_order, bw_cutoff)
    -> (processed_signal, effective_fs)
    Full pipeline: bandpass → baseline removal → optional resample
"""

from __future__ import annotations

import importlib
from typing import Any, cast

import numpy as np


_sp_signal = cast(Any, importlib.import_module("scipy.signal"))


def bandpass_filter(
    ecg: np.ndarray,
    fs: int,
    lowcut: float = 0.5,
    highcut: float = 40.0,
    order: int = 4,
) -> np.ndarray:
    """
    Apply a zero-phase Butterworth bandpass filter.

    Parameters
    ----------
    ecg     : 1-D float64 ECG signal
    fs      : sampling frequency (Hz)
    lowcut  : lower cutoff frequency (Hz), default 0.5
    highcut : upper cutoff frequency (Hz), default 40.0
    order   : filter order, default 4

    Returns
    -------
    filtered : filtered signal, same shape as input
    """
    ecg = np.asarray(ecg, dtype=np.float64)
    nyq = fs / 2.0
    low = lowcut / nyq
    high = highcut / nyq
    # Clip to valid range
    low = max(low, 1e-4)
    high = min(high, 1.0 - 1e-4)
    sos = _sp_signal.butter(order, [low, high], btype="bandpass", output="sos")
    return np.asarray(_sp_signal.sosfiltfilt(sos, ecg), dtype=np.float64)


def remove_baseline_wander(
    ecg: np.ndarray,
    fs: int,
    cutoff: float = 0.5,
    order: int = 4,
) -> np.ndarray:
    """
    Remove baseline wander using a high-pass filter.

    A zero-phase Butterworth high-pass filter is applied, which suppresses
    low-frequency drift (respiratory motion, electrode movement) while
    preserving the ECG waveform.

    Parameters
    ----------
    ecg    : 1-D float64 ECG signal
    fs     : sampling frequency (Hz)
    cutoff : high-pass cutoff frequency (Hz), default 0.5
    order  : filter order, default 4

    Returns
    -------
    corrected : baseline-corrected signal
    """
    ecg = np.asarray(ecg, dtype=np.float64)
    nyq = fs / 2.0
    normalized_cutoff = max(cutoff / nyq, 1e-4)
    normalized_cutoff = min(normalized_cutoff, 1.0 - 1e-4)
    sos = _sp_signal.butter(order, normalized_cutoff, btype="highpass", output="sos")
    return np.asarray(_sp_signal.sosfiltfilt(sos, ecg), dtype=np.float64)


def resample_signal(
    ecg: np.ndarray,
    fs_in: int,
    fs_out: int = 250,
) -> tuple[np.ndarray, int]:
    """
    Resample ECG to a target sampling rate using polyphase filtering.

    Parameters
    ----------
    ecg    : 1-D ECG signal
    fs_in  : original sampling frequency (Hz)
    fs_out : target sampling frequency (Hz), default 250

    Returns
    -------
    resampled : resampled signal
    fs_out    : target sampling frequency (echoed back)
    """
    if fs_in == fs_out:
        return np.asarray(ecg, dtype=np.float64), fs_out

    ecg = np.asarray(ecg, dtype=np.float64)
    from math import gcd
    g = gcd(int(fs_in), int(fs_out))
    up = int(fs_out) // g
    down = int(fs_in) // g
    resampled = _sp_signal.resample_poly(ecg, up, down)
    return resampled.astype(np.float64), fs_out


def preprocess(
    ecg: np.ndarray,
    fs: int,
    target_fs: int | None = 250,
    bp_low: float = 0.5,
    bp_high: float = 40.0,
    bp_order: int = 4,
    bw_cutoff: float = 0.5,
) -> tuple[np.ndarray, int]:
    """
    Full preprocessing pipeline.

    Steps (in order):
      1. Bandpass filter (bp_low – bp_high Hz)
      2. Baseline wander removal (high-pass at bw_cutoff Hz)
      3. Optional resample to target_fs

    Parameters
    ----------
    ecg       : raw 1-D ECG signal
    fs        : original sampling frequency (Hz)
    target_fs : resample to this rate; pass None to skip resampling
    bp_low    : bandpass lower cutoff (Hz)
    bp_high   : bandpass upper cutoff (Hz)
    bp_order  : Butterworth filter order
    bw_cutoff : baseline wander removal cutoff (Hz)

    Returns
    -------
    processed : preprocessed signal
    effective_fs : sampling frequency of returned signal
    """
    ecg = np.asarray(ecg, dtype=np.float64)

    # Step 1: bandpass
    ecg = bandpass_filter(ecg, fs, lowcut=bp_low, highcut=bp_high, order=bp_order)

    # Step 2: baseline wander removal (high-pass already applied in bandpass,
    # but a dedicated pass ensures strong suppression)
    ecg = remove_baseline_wander(ecg, fs, cutoff=bw_cutoff, order=bp_order)

    # Step 3: optional resample
    effective_fs = fs
    if target_fs is not None and target_fs != fs:
        ecg, effective_fs = resample_signal(ecg, fs, target_fs)

    return ecg, effective_fs
