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

    # Rule 1: terminal rhythms override everything
    if strip_label in _TERMINAL_RHYTHMS:
        return strip_label

    # No beat-level data — return strip label as-is
    if not beat_labels:
        return strip_label

    n_beats = len(beat_labels)
    count = Counter(beat_labels)
    pvc_frac = count.get(ArrhythmiaClass.PVC, 0) / n_beats

    # Rule 2: predominantly PVC → VT
    if strip_label == ArrhythmiaClass.NSR and pvc_frac > 0.40:
        return ArrhythmiaClass.VT

    # Rule 3: significant PVCs in NSR context — keep NSR (PVC burden noted elsewhere)
    # (No change to label; callers can inspect beat_labels for PVC burden)

    return strip_label
