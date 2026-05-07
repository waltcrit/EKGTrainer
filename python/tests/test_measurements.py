"""
Tests for measurement helpers: _qrs_width, _detect_j_point, _pr_interval, _qtc.
All tests operate on synthetic templates — no image digitization required.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from analyze_ecg import (
    _detect_j_point,
    _pr_interval,
    _qrs_width,
    _qtc,
)

FS = 250


def _make_template(
    fs: int = FS,
    qrs_width_ms: float = 80.0,
    p_amplitude: float = 0.20,
    t_amplitude: float = 0.30,
    inverted_p: bool = False,
) -> np.ndarray:
    """
    Build a synthetic beat template centred on R-peak (mid = len//2).
    Template length = 600 ms = 150 samples at 250 Hz.
    """
    length = int(0.6 * fs)
    tmpl = np.zeros(length, dtype=np.float64)
    mid = length // 2

    # QRS spike
    qrs_w = max(4, int(qrs_width_ms / 1000 * fs))
    half_q = qrs_w // 2
    for i in range(qrs_w):
        tmpl[mid - half_q + i] = 1.5 * (1 - abs(i - half_q) / half_q)

    # P-wave ~150 ms before R
    p_center = mid - int(0.15 * fs)
    p_w = int(0.04 * fs)
    for i in range(-p_w, p_w + 1):
        idx = p_center + i
        if 0 <= idx < length:
            sign = -1 if inverted_p else 1
            tmpl[idx] += sign * p_amplitude * np.exp(-0.5 * (i / (p_w / 2)) ** 2)

    # T-wave ~300 ms after R
    t_center = mid + int(0.30 * fs)
    t_w = int(0.06 * fs)
    for i in range(-t_w, t_w + 1):
        idx = t_center + i
        if 0 <= idx < length:
            tmpl[idx] += t_amplitude * np.exp(-0.5 * (i / (t_w / 2)) ** 2)

    return tmpl


class TestQrsWidth:

    def test_narrow_qrs(self):
        tmpl = _make_template(qrs_width_ms=80.0)
        width_ms, wide = _qrs_width(tmpl, FS)
        assert width_ms is not None
        assert width_ms < 120.0, f"Expected narrow QRS, got {width_ms:.1f} ms"
        assert wide is False

    def test_wide_qrs(self):
        tmpl = _make_template(qrs_width_ms=140.0)
        width_ms, wide = _qrs_width(tmpl, FS)
        assert width_ms is not None
        assert width_ms >= 120.0, f"Expected wide QRS, got {width_ms:.1f} ms"
        assert wide is True

    def test_none_template(self):
        width_ms, wide = _qrs_width(None, FS)
        assert width_ms is None
        assert wide is False

    def test_empty_template(self):
        width_ms, wide = _qrs_width(np.array([]), FS)
        assert width_ms is None
        assert wide is False


class TestDetectJPoint:

    def test_returns_positive_offset(self):
        tmpl = _make_template(qrs_width_ms=80.0)
        j = _detect_j_point(tmpl, FS)
        assert j > 0

    def test_j_within_physiologic_range(self):
        tmpl = _make_template(qrs_width_ms=80.0)
        j = _detect_j_point(tmpl, FS)
        # J-point should be 20–100 ms after R
        assert int(0.02 * FS) <= j <= int(0.10 * FS), f"J-point {j} out of range"

    def test_none_returns_default(self):
        j = _detect_j_point(None, FS)
        assert j == max(1, int(0.04 * FS))

    def test_wide_qrs_j_later(self):
        narrow = _detect_j_point(_make_template(qrs_width_ms=80.0), FS)
        wide = _detect_j_point(_make_template(qrs_width_ms=140.0), FS)
        assert wide >= narrow, "Wide QRS should produce later or equal J-point"


class TestPrInterval:

    def test_upright_p_wave_detected(self):
        tmpl = _make_template(p_amplitude=0.20, inverted_p=False)
        pr_ms, p_present, morphology = _pr_interval(tmpl, FS)
        assert p_present is True
        assert morphology == "upright"
        assert pr_ms is not None
        assert 100 < pr_ms < 260, f"PR {pr_ms:.1f} ms outside expected range"

    def test_inverted_p_wave_detected(self):
        tmpl = _make_template(p_amplitude=0.20, inverted_p=True)
        pr_ms, p_present, morphology = _pr_interval(tmpl, FS)
        assert p_present is True
        assert morphology == "inverted"

    def test_absent_p_wave(self):
        tmpl = _make_template(p_amplitude=0.0)
        pr_ms, p_present, morphology = _pr_interval(tmpl, FS)
        assert p_present is False
        assert pr_ms is None
        assert morphology is None

    def test_none_template(self):
        pr_ms, p_present, morphology = _pr_interval(None, FS)
        assert p_present is False
        assert pr_ms is None

    def test_calibrated_absolute_threshold(self):
        # Very small P-wave (5% of R ~= 0.075 mV) should be absent when calibrated
        tmpl = _make_template(p_amplitude=0.05)
        _, p_present_uncalib, _ = _pr_interval(tmpl, FS, calibrated=False)
        _, p_present_calib, _ = _pr_interval(tmpl, FS, calibrated=True)
        # Calibrated uses 0.10 mV absolute; 0.05 mV should fail
        assert p_present_calib is False


class TestQtc:

    def test_returns_tuple_of_five(self):
        tmpl = _make_template()
        rr = [800.0] * 8
        result = _qtc(tmpl, rr, FS, heart_rate_bpm=75.0)
        assert len(result) == 5

    def test_qt_in_physiologic_range(self):
        tmpl = _make_template()
        rr = [800.0] * 8
        qt_ms, qtc_b, qtc_f, prolonged, method = _qtc(tmpl, rr, FS, heart_rate_bpm=75.0)
        assert qt_ms is not None
        assert 200 < qt_ms < 600, f"QT {qt_ms:.1f} ms outside expected range"

    def test_bazett_at_normal_rate(self):
        tmpl = _make_template()
        rr = [857.0] * 8  # ~70 bpm
        _, _, _, _, method = _qtc(tmpl, rr, FS, heart_rate_bpm=70.0)
        assert method == "bazett"

    def test_fridericia_at_tachycardia(self):
        tmpl = _make_template()
        rr = [500.0] * 8  # 120 bpm
        _, _, _, _, method = _qtc(tmpl, rr, FS, heart_rate_bpm=120.0)
        assert method == "fridericia"

    def test_fridericia_at_bradycardia(self):
        tmpl = _make_template()
        rr = [1200.0] * 8  # 50 bpm
        _, _, _, _, method = _qtc(tmpl, rr, FS, heart_rate_bpm=50.0)
        assert method == "fridericia"

    def test_none_template_returns_nones(self):
        qt, qtcb, qtcf, prolonged, method = _qtc(None, [800.0] * 5, FS, 75.0)
        assert qt is None
        assert qtcb is None
        assert qtcf is None
        assert prolonged is None
