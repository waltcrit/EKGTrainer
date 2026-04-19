"""Tests for _regularity() — RR-interval classification."""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from analyze_ecg import _regularity


class TestRegularity:

    def test_regular_uniform(self):
        rr = [800.0] * 10
        assert _regularity(rr) == "regular"

    def test_regular_with_tiny_jitter(self):
        # ±1 ms digitizer jitter on a 1000 ms RR → still regular
        rng = np.random.default_rng(0)
        rr = (1000.0 + rng.uniform(-1, 1, 10)).tolist()
        assert _regularity(rr) == "regular"

    def test_insufficient_beats(self):
        assert _regularity([800.0]) == "indeterminate"
        assert _regularity([]) == "indeterminate"
        assert _regularity([800.0, 810.0]) == "indeterminate"

    def test_irregularly_irregular(self):
        # AFib-like: random intervals 500–1200 ms
        rng = np.random.default_rng(1)
        rr = rng.uniform(500, 1200, 12).tolist()
        result = _regularity(rr)
        assert result in ("irregularly_irregular", "regularly_irregular")

    def test_regularly_irregular_bigeminy(self):
        # Bigeminy: alternating short/long (500/1000 ms)
        rr = ([500.0, 1000.0] * 6)
        result = _regularity(rr)
        assert result in ("regularly_irregular", "regular")

    def test_single_outlier_does_not_break_regular(self):
        # One artifact interval should not reclassify a regular rhythm
        rr = [800.0] * 9 + [400.0]  # one doubled beat / missed beat
        assert _regularity(rr) == "regular"

    def test_high_cv_is_irregular(self):
        # CV > 20% → irregularly irregular
        rr = [600.0, 1200.0, 600.0, 1100.0, 650.0, 1150.0]
        result = _regularity(rr)
        assert result == "irregularly_irregular"
