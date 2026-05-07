"""
Post-processing for arrhythmia predictions.

Implements:
  1. Temporal smoothing — majority vote over a sliding window
  2. Physiologic constraints — hard rules that prevent clinically impossible
     label sequences (e.g., VF alternating with NSR beat-by-beat)

Public API
----------
smooth_predictions(labels, window)
    -> list[str]   — smoothed label sequence

apply_physiologic_constraints(strip_label, beat_labels)
    -> str         — final rhythm label after constraint enforcement
"""

from __future__ import annotations

from collections import Counter
from typing import Mapping

from arrhythmia.constants import ArrhythmiaClass


# ---------------------------------------------------------------------------
# Temporal smoothing
# ---------------------------------------------------------------------------

def smooth_predictions(
    labels: list[str],
    window: int = 5,
) -> list[str]:
    """
    Apply sliding-window majority-vote smoothing to a label sequence.

    Prevents rapid oscillation between classes that is physiologically
    implausible (e.g., NSR ↔ AF every other window).

    Parameters
    ----------
    labels : ordered list of predicted labels (one per window/beat)
    window : number of consecutive predictions to vote over (default 5)

    Returns
    -------
    smoothed : list of smoothed labels, same length as input
    """
    if len(labels) <= window:
        if not labels:
            return []
        dominant = Counter(labels).most_common(1)[0][0]
        return [dominant] * len(labels)

    half = window // 2
    smoothed: list[str] = []
    for i in range(len(labels)):
        lo = max(0, i - half)
        hi = min(len(labels), i + half + 1)
        vote = Counter(labels[lo:hi]).most_common(1)[0][0]
        smoothed.append(vote)
    return smoothed


# ---------------------------------------------------------------------------
# Physiologic constraints
# ---------------------------------------------------------------------------

# Labels that imply a life-threatening state that cannot co-exist with NSR
_TERMINAL_RHYTHMS = frozenset({
    ArrhythmiaClass.VF,
    ArrhythmiaClass.ASYS,
})

# Labels where beat-level PAC/PVC detection should be suppressed
# (the beat detector is unreliable during these rhythms)
_SUPPRESS_BEAT_DETAIL = frozenset({
    ArrhythmiaClass.VF,
    ArrhythmiaClass.ASYS,
    ArrhythmiaClass.AFL,
})


def apply_physiologic_constraints(
    strip_label: str,
    beat_labels: list[str] | None = None,
    strip_features: Mapping[str, object] | None = None,
) -> str:
    """
    Enforce physiologically plausible final rhythm classification.

    Rules (in priority order):
    1. If the strip is classified as VF or Asystole, override all beat-level
       findings — the patient is in cardiac arrest; per-beat labels are noise.
    2. If the strip is classified as NSR but >40% of beats are PVC,
       upgrade to VT (runs of PVCs).
    3. If the strip is classified as NSR but >30% of beats are PVC
       (but ≤40%), annotate as PVC with NSR background (keep NSR).
    4. Any other combination: trust the strip-level classification.

    Parameters
    ----------
    strip_label : strip-level arrhythmia class (from rhythm model or classical)
    beat_labels : per-beat arrhythmia classes from beat model (may be empty)

    Returns
    -------
    final_label : constrained arrhythmia class string
    """
    if beat_labels is None:
        beat_labels = []
    strip_features = strip_features or {}

    def _get_float(name: str, default: float = float("nan")) -> float:
        v = strip_features.get(name, default)
        if isinstance(v, (int, float)):
            return float(v)
        return default

    num_beats = _get_float("num_beats", float("nan"))
    signal_power = _get_float("signal_power", float("nan"))
    patterned = _get_float("patterned_irregularity_score", float("nan"))
    spectral_entropy = _get_float("spectral_entropy", float("nan"))
    dominant_freq = _get_float("dominant_freq_hz", float("nan"))

    # Rule 1: terminal rhythms override everything
    # But guard against obvious upstream errors: do not emit terminal labels
    # when the signal clearly contains multiple beats and lacks spectral evidence.
    if strip_label == ArrhythmiaClass.ASYS:
        # Asystole should have ~0 beats and very low power.
        if (isinstance(num_beats, float) and num_beats >= 2) or (isinstance(signal_power, float) and signal_power > 0.01):
            return ArrhythmiaClass.NSR
        return strip_label

    if strip_label == ArrhythmiaClass.VF:
        # VF should have high spectral entropy with a dominant band in ~2–10 Hz.
        if (
            isinstance(spectral_entropy, float)
            and isinstance(dominant_freq, float)
            and spectral_entropy > 0.75
            and 2.0 <= dominant_freq <= 10.0
        ):
            return strip_label
        # If we have many detected beats, it's unlikely to be true VF.
        if isinstance(num_beats, float) and num_beats >= 6:
            return ArrhythmiaClass.AF if (isinstance(patterned, float) and patterned < 0.25) else ArrhythmiaClass.NSR
        return strip_label

    # No beat-level data — return strip label as-is
    if not beat_labels:
        return strip_label

    n_beats = len(beat_labels)
    count = Counter(beat_labels)
    pvc_frac = count.get(ArrhythmiaClass.PVC, 0) / n_beats
    pac_frac = count.get(ArrhythmiaClass.PAC, 0) / n_beats

    # AF vs ectopy guard: patterned irregularity + substantial ectopy burden
    if strip_label == ArrhythmiaClass.AF:
        if isinstance(patterned, float) and patterned > 0.35 and (pvc_frac > 0.20 or pac_frac > 0.20):
            return ArrhythmiaClass.PVC if pvc_frac >= pac_frac else ArrhythmiaClass.PAC

    # Rule 2: predominantly PVC → VT
    if strip_label == ArrhythmiaClass.NSR and pvc_frac > 0.40:
        return ArrhythmiaClass.VT

    # Rule 3: significant PVCs in NSR context — keep NSR (PVC burden noted elsewhere)
    # (No change to label; callers can inspect beat_labels for PVC burden)

    return strip_label
