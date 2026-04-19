"""ECG image digitization: ECG-Digitiser (preferred) or OpenCV fallback."""
from __future__ import annotations

import logging
from typing import cast

import numpy as np
from numpy.typing import NDArray

from ecg.types import DigitizedResult, SignalArray

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Hoisted optional imports
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
    from ecg_digitiser.digitiser import ECGDigitiser
    _ecg_digitiser_available = True
except ImportError:
    _ecg_digitiser_available = False


def digitize_image(image_path: str | None = None, image_bytes: bytes | None = None) -> DigitizedResult:
    """
    Convert an ECG image to a digital signal using ECG-Digitiser or OpenCV fallback.
    Accepts either a file path or raw image bytes.
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
                "calibrated": True,
            }
        except Exception as e:
            logger.warning(f"ECG-Digitiser failed: {type(e).__name__}: {e}; falling back to OpenCV")

    return _fallback_digitize(image_path, image_bytes)


def _detect_grid_calibration(gray: NDArray[np.uint8]) -> dict[str, float] | None:
    """
    Detect ECG paper grid spacing via FFT on column projections.
    Standard ECG paper: 25 mm/s, 10 mm/mV; 1 mm small square = 40 ms.
    Returns dict with sampling_rate_hz, pixels_per_mv, grid_px_horiz, or None.
    """
    _, w = gray.shape

    col_sum = gray.astype(float).sum(axis=0)
    col_sum -= col_sum.mean()
    fft_h = np.abs(np.fft.rfft(col_sum))
    freqs_h = np.fft.rfftfreq(w)

    with np.errstate(divide="ignore", invalid="ignore"):
        periods_h = np.where(freqs_h > 0, 1.0 / freqs_h, np.inf)
    mask_h = (4 < periods_h) & (periods_h < 25)
    if not mask_h.any():
        return None
    grid_px_horiz = float(periods_h[np.argmax(fft_h * mask_h)])

    peak_mag = float(np.max(fft_h * mask_h))
    mean_mag = float(np.mean(fft_h[mask_h]))
    if peak_mag < mean_mag * 3:
        return None

    sampling_rate_hz = grid_px_horiz / 0.040
    pixels_per_mv = grid_px_horiz * 10.0

    return {
        "sampling_rate_hz": sampling_rate_hz,
        "pixels_per_mv":    pixels_per_mv,
        "grid_px_horiz":    grid_px_horiz,
    }


def _fallback_digitize(image_path: str | None = None, image_bytes: bytes | None = None) -> DigitizedResult:
    """Grid-calibrated OpenCV digitizer. Accepts image_path or image_bytes."""
    if not _cv2_available:
        raise RuntimeError("opencv-python is not installed. Cannot digitize ECG image.")

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

    cal = _detect_grid_calibration(gray)
    if cal:
        sampling_rate = int(round(cal["sampling_rate_hz"]))
        pixels_per_mv = cal["pixels_per_mv"]
        method = f"fallback-opencv-calibrated({sampling_rate}Hz)"
        calibrated = True
    else:
        sampling_rate = 179
        pixels_per_mv = None
        method = "fallback-opencv-uncalibrated"
        calibrated = False

    sampling_rate = min(sampling_rate, 500)

    inv = (255 - gray).astype(float)
    margin = max(1, w // 100)
    inv[:, :margin]  = 0
    inv[:, -margin:] = 0
    v_margin = max(1, h // 20)
    inv[:v_margin, :] = 0
    inv[-v_margin:, :] = 0

    trace_row = np.argmax(inv, axis=0).astype(float)

    if not _scipy_ndimage_available:
        raise RuntimeError("scipy is not installed. Cannot digitize ECG image.")
    trace_row = scipy_ndimage.median_filter(trace_row, size=3).astype(float)

    signal = (h - 1) - trace_row

    bl_window = max(3, int(sampling_rate * 0.6) | 1)
    baseline = cast(SignalArray, scipy_ndimage.median_filter(signal, size=bl_window, mode="nearest"))
    signal = signal - baseline

    if calibrated and pixels_per_mv is not None and pixels_per_mv > 0:
        signal = signal / pixels_per_mv
    elif signal.std() > 0:
        signal = signal / signal.std() * 0.5

    spike_thr = float(np.percentile(np.abs(signal), 99.5)) * 2.0
    spike_mask = np.abs(signal) > spike_thr
    labeled_spikes, n_spikes = scipy_ndimage.label(spike_mask)
    for spike_id in range(1, n_spikes + 1):
        spike_idx = np.where(labeled_spikes == spike_id)[0]
        if len(spike_idx) <= 2:
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
        "calibrated":    calibrated,
    }
