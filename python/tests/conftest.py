"""
Shared fixtures for ECG analysis tests.

Synthetic ECG signals are generated using basic trigonometry — no real patient
data required. All fixtures aim to produce physiologically plausible values so
assertions can be tight without being fragile.
"""
from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray


FS = 250  # synthetic sampling rate (Hz)


def _make_qrs_spike(width_samples: int, amplitude: float = 1.5) -> NDArray[np.float64]:
    """Return a triangular QRS-like spike centred at zero."""
    half = width_samples // 2
    rising = np.linspace(0, amplitude, half)
    falling = np.linspace(amplitude, 0, width_samples - half)
    return np.concatenate([rising, falling])


def synthetic_ecg(
    hr_bpm: float = 60.0,
    duration_s: float = 10.0,
    fs: int = FS,
    qrs_width_ms: float = 80.0,
    p_amplitude: float = 0.15,
    noise_std: float = 0.01,
    irregular: bool = False,
) -> NDArray[np.float64]:
    """
    Build a synthetic Lead II ECG with recognisable PQRST morphology.

    Parameters
    ----------
    hr_bpm       : target heart rate
    duration_s   : total signal duration
    fs           : sampling rate
    qrs_width_ms : QRS complex width in ms
    p_amplitude  : P-wave amplitude relative to R (R amplitude = 1.5 mV)
    noise_std    : white Gaussian noise standard deviation
    irregular    : if True, add ±15 % RR jitter (simulates mild arrhythmia)
    """
    n_samples = int(duration_s * fs)
    signal = np.zeros(n_samples, dtype=np.float64)

    rr_samples = int(fs * 60.0 / hr_bpm)
    qrs_w = max(4, int(qrs_width_ms / 1000 * fs))

    beat_offset = rr_samples // 4  # first beat starts 1/4 RR into signal
    t = beat_offset
    while t + rr_samples < n_samples:
        # P-wave: small Gaussian bump ~160 ms before R
        p_center = t - int(0.16 * fs)
        p_width = int(0.04 * fs)
        if p_center > 0 and p_center + p_width < n_samples:
            p_x = np.arange(-p_width, p_width + 1)
            p_wave = p_amplitude * np.exp(-0.5 * (p_x / (p_width / 2)) ** 2)
            lo = max(0, p_center - p_width)
            hi = min(n_samples, p_center + p_width + 1)
            signal[lo:hi] += p_wave[: hi - lo]

        # QRS spike
        if t + qrs_w < n_samples:
            signal[t : t + qrs_w] += _make_qrs_spike(qrs_w)

        # T-wave: broad Gaussian ~300 ms after R
        t_center = t + int(0.30 * fs)
        t_width = int(0.08 * fs)
        if t_center + t_width < n_samples:
            t_x = np.arange(-t_width, t_width + 1)
            t_wave = 0.3 * np.exp(-0.5 * (t_x / (t_width / 2)) ** 2)
            lo = max(0, t_center - t_width)
            hi = min(n_samples, t_center + t_width + 1)
            signal[lo:hi] += t_wave[: hi - lo]

        step = rr_samples
        if irregular:
            step = int(rr_samples * (1.0 + np.random.uniform(-0.15, 0.15)))
        t += max(step, int(0.25 * fs))  # enforce physiologic minimum

    signal += np.random.default_rng(42).normal(0, noise_std, n_samples)
    return signal


def synthetic_afib_ecg(
    mean_hr: float = 80.0,
    duration_s: float = 10.0,
    fs: int = FS,
) -> NDArray[np.float64]:
    """Fibrillatory baseline + irregular narrow QRS, no P-waves."""
    n_samples = int(duration_s * fs)
    rng = np.random.default_rng(7)

    # Fine fibrillatory baseline (350–600 Hz chaos, sampled at fs)
    fib = rng.normal(0, 0.07, n_samples)

    signal = fib.copy()
    rr_mean = int(fs * 60.0 / mean_hr)
    qrs_w = max(4, int(0.08 * fs))

    t = rr_mean // 3
    while t + rr_mean < n_samples:
        if t + qrs_w < n_samples:
            signal[t : t + qrs_w] += _make_qrs_spike(qrs_w, amplitude=1.2)
        jitter = int(rng.uniform(-rr_mean * 0.30, rr_mean * 0.30))
        t += max(rr_mean + jitter, int(0.25 * fs))

    return signal


@pytest.fixture
def sinus_60bpm() -> NDArray[np.float64]:
    return synthetic_ecg(hr_bpm=60.0)


@pytest.fixture
def sinus_100bpm() -> NDArray[np.float64]:
    return synthetic_ecg(hr_bpm=100.0)


@pytest.fixture
def irregular_ecg() -> NDArray[np.float64]:
    return synthetic_ecg(hr_bpm=75.0, irregular=True)


@pytest.fixture
def afib_ecg() -> NDArray[np.float64]:
    return synthetic_afib_ecg()


@pytest.fixture
def wide_qrs_ecg() -> NDArray[np.float64]:
    return synthetic_ecg(hr_bpm=70.0, qrs_width_ms=140.0)
