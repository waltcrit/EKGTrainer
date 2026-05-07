"""Shared TypedDicts and type aliases for the ECG analysis pipeline."""
from __future__ import annotations

from typing import NotRequired, Protocol, TypeAlias, TypedDict

import numpy as np
from numpy.typing import NDArray

SignalArray: TypeAlias = NDArray[np.float64]
SignalMap: TypeAlias = dict[str, SignalArray]


class DigitizedResult(TypedDict):
    signals: SignalMap
    sampling_rate: int
    method: str
    calibrated: bool


class STLeadResult(TypedDict):
    elevation: bool
    depression: bool
    mean_mv: float


STResults: TypeAlias = dict[str, STLeadResult]


class PipelineClassification(TypedDict, total=False):
    primary_rhythm: str
    display_name: str
    strip_label: str
    confidence: float
    beat_labels: list[str]
    used_deep_learning: bool
    notes: list[str]
    error: str


class SignalMeasurements(TypedDict):
    r_peaks: list[int]
    rr_intervals_ms: list[float]
    heart_rate_bpm: float
    regularity: str
    p_waves_present: bool
    p_wave_morphology: NotRequired[str | None]
    pr_interval_ms: float | None
    qrs_duration_ms: float | None
    qrs_wide: bool
    qt_ms: float | None
    qtc_ms: float | None
    qtcf_ms: NotRequired[float | None]
    qtc_method: NotRequired[str]
    qtc_prolonged: bool | None
    st: STResults
    num_beats: int
    rhythm_lead: str
    amplitude_calibrated: NotRequired[bool]
    afib_hint: NotRequired[bool]
    vf_morphology: NotRequired[bool]
    p_peaks: NotRequired[list[int]]
    pp_intervals_ms: NotRequired[list[float]]


class InferenceResultLike(Protocol):
    primary_rhythm: object
    strip_label: object
    confidence: float
    beat_labels: list[str]
    used_deep_learning: bool
    notes: list[str]
