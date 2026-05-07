"""
Golden-signal integration tests for analyze_signal().

These tests digitize a synthetic signal and assert that the key measurements
fall within clinically plausible ranges. They are deliberately loose (±10 bpm,
±20 ms) because the synthetic signal is idealized, not a real ECG scan.
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from analyze_ecg import analyze_signal
from tests.conftest import synthetic_ecg, synthetic_afib_ecg, FS


class TestAnalyzeSignalGolden:

    def test_60bpm_heart_rate(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        assert 50 <= m["heart_rate_bpm"] <= 70, f"HR={m['heart_rate_bpm']}"

    def test_100bpm_heart_rate(self, sinus_100bpm):
        m = analyze_signal({"II": sinus_100bpm}, FS)
        assert 90 <= m["heart_rate_bpm"] <= 110, f"HR={m['heart_rate_bpm']}"

    def test_regular_rhythm(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        assert m["regularity"] == "regular"

    def test_beat_count_approx(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        # 10 s at 60 bpm → ~10 beats
        assert 7 <= m["num_beats"] <= 13, f"beats={m['num_beats']}"

    def test_narrow_qrs(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        assert m["qrs_wide"] is False

    def test_wide_qrs_detected(self, wide_qrs_ecg):
        m = analyze_signal({"II": wide_qrs_ecg}, FS)
        assert m["qrs_wide"] is True, "Wide QRS should be detected"

    def test_p_waves_present_in_sinus(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        assert m["p_waves_present"] is True

    def test_measurements_keys_complete(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        required = {
            "r_peaks", "rr_intervals_ms", "heart_rate_bpm", "regularity",
            "p_waves_present", "pr_interval_ms", "qrs_duration_ms",
            "qrs_wide", "qt_ms", "qtc_ms", "qtc_prolonged", "st",
            "num_beats", "rhythm_lead",
        }
        missing = required - set(m.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_rhythm_lead_reported(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        assert m["rhythm_lead"] == "II"

    def test_afib_irregular(self, afib_ecg):
        m = analyze_signal({"II": afib_ecg}, FS)
        assert m["regularity"] in ("irregularly_irregular", "regularly_irregular")

    def test_calibrated_flag_propagates(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS, calibrated=True)
        assert m.get("amplitude_calibrated") is True

    def test_afib_hint_no_p_waves(self, afib_ecg):
        m = analyze_signal({"II": afib_ecg}, FS)
        # AFib hint only fires when both conditions hold
        if m.get("afib_hint"):
            assert m["regularity"] == "irregularly_irregular"
            assert m["p_waves_present"] is False

    def test_multi_lead_picks_best(self):
        """With two leads, analyze_signal should pick the one with higher RMS."""
        signal_strong = synthetic_ecg(hr_bpm=60.0) * 2.0   # stronger signal
        signal_weak = synthetic_ecg(hr_bpm=60.0) * 0.1    # weaker signal
        m = analyze_signal({"I": signal_weak, "II": signal_strong}, FS)
        assert m["rhythm_lead"] == "II"

    def test_rr_intervals_match_hr(self, sinus_60bpm):
        m = analyze_signal({"II": sinus_60bpm}, FS)
        rr = m["rr_intervals_ms"]
        if rr:
            hr_from_rr = 60000.0 / np.mean(rr)
            assert abs(hr_from_rr - m["heart_rate_bpm"]) < 1.0


class TestAnalyzeSignalEdgeCases:

    def test_too_short_signal_raises(self):
        short = np.zeros(100)  # < 2 seconds at 250 Hz
        with pytest.raises(RuntimeError, match="too short"):
            analyze_signal({"II": short}, FS)

    def test_flat_signal_survives(self):
        # Flat line — no peaks detectable; should not raise, just return zeros
        flat = np.zeros(int(10 * FS))
        try:
            m = analyze_signal({"II": flat}, FS)
            assert m["num_beats"] == 0 or m["heart_rate_bpm"] == 0.0
        except RuntimeError:
            pass  # acceptable if pipeline explicitly rejects flat signals
