"""
Canonical arrhythmia classes supported by the EKG Trainer pipeline.

Provides:
  - ArrhythmiaClass  : string enum of canonical labels
  - DISPLAY_NAMES    : label -> human-readable name
  - UI_STYLES        : label -> Tailwind-compatible color tokens + hex fallback
  - EXPLANATIONS     : label -> short clinical description (1-2 sentences)
  - BEAT_LEVEL       : set of labels classified at beat level
  - STRIP_LEVEL      : set of labels classified at rhythm-strip level
"""

from __future__ import annotations
from enum import Enum


class ArrhythmiaClass(str, Enum):
    """Canonical label strings used throughout the pipeline."""

    NSR   = "NSR"   # Normal Sinus Rhythm
    SB    = "SB"    # Sinus Bradycardia
    ST    = "ST"    # Sinus Tachycardia
    AF    = "AF"    # Atrial Fibrillation
    AFL   = "AFL"   # Atrial Flutter
    SVT   = "SVT"   # Supraventricular Tachycardia
    PAC   = "PAC"   # Premature Atrial Contraction
    PVC   = "PVC"   # Premature Ventricular Contraction
    VT    = "VT"    # Ventricular Tachycardia
    VF    = "VF"    # Ventricular Fibrillation
    ASYS  = "ASYS"  # Asystole


# ---------------------------------------------------------------------------
# Display names
# ---------------------------------------------------------------------------
DISPLAY_NAMES: dict[str, str] = {
    ArrhythmiaClass.NSR:  "Normal Sinus Rhythm",
    ArrhythmiaClass.SB:   "Sinus Bradycardia",
    ArrhythmiaClass.ST:   "Sinus Tachycardia",
    ArrhythmiaClass.AF:   "Atrial Fibrillation",
    ArrhythmiaClass.AFL:  "Atrial Flutter",
    ArrhythmiaClass.SVT:  "Supraventricular Tachycardia",
    ArrhythmiaClass.PAC:  "Premature Atrial Contraction",
    ArrhythmiaClass.PVC:  "Premature Ventricular Contraction",
    ArrhythmiaClass.VT:   "Ventricular Tachycardia",
    ArrhythmiaClass.VF:   "Ventricular Fibrillation",
    ArrhythmiaClass.ASYS: "Asystole",
}

# ---------------------------------------------------------------------------
# UI styles
# Tailwind color class + hex fallback for non-Tailwind contexts.
# ---------------------------------------------------------------------------
UI_STYLES: dict[str, dict[str, str]] = {
    ArrhythmiaClass.NSR:  {"tailwind": "text-green-600",  "hex": "#16a34a", "bg": "#dcfce7"},
    ArrhythmiaClass.SB:   {"tailwind": "text-yellow-600", "hex": "#ca8a04", "bg": "#fef9c3"},
    ArrhythmiaClass.ST:   {"tailwind": "text-orange-500", "hex": "#f97316", "bg": "#ffedd5"},
    ArrhythmiaClass.AF:   {"tailwind": "text-red-500",    "hex": "#ef4444", "bg": "#fee2e2"},
    ArrhythmiaClass.AFL:  {"tailwind": "text-red-400",    "hex": "#f87171", "bg": "#fee2e2"},
    ArrhythmiaClass.SVT:  {"tailwind": "text-pink-500",   "hex": "#ec4899", "bg": "#fce7f3"},
    ArrhythmiaClass.PAC:  {"tailwind": "text-blue-500",   "hex": "#3b82f6", "bg": "#dbeafe"},
    ArrhythmiaClass.PVC:  {"tailwind": "text-purple-600", "hex": "#9333ea", "bg": "#f3e8ff"},
    ArrhythmiaClass.VT:   {"tailwind": "text-red-700",    "hex": "#b91c1c", "bg": "#fee2e2"},
    ArrhythmiaClass.VF:   {"tailwind": "text-red-900",    "hex": "#7f1d1d", "bg": "#fee2e2"},
    ArrhythmiaClass.ASYS: {"tailwind": "text-gray-700",   "hex": "#374151", "bg": "#f3f4f6"},
}

# ---------------------------------------------------------------------------
# Short clinical explanations
# ---------------------------------------------------------------------------
EXPLANATIONS: dict[str, str] = {
    ArrhythmiaClass.NSR: (
        "Regular rhythm originating from the sinoatrial node at 60–100 bpm. "
        "P waves precede every QRS; PR interval 120–200 ms."
    ),
    ArrhythmiaClass.SB: (
        "Sinus rhythm with rate < 60 bpm. Normal P-QRS relationship preserved; "
        "can be physiologic (athletes) or pathologic."
    ),
    ArrhythmiaClass.ST: (
        "Sinus rhythm with rate > 100 bpm. Normal P-QRS relationship; "
        "usually a secondary response to fever, pain, hypovolemia, or anxiety."
    ),
    ArrhythmiaClass.AF: (
        "Disorganized atrial activity (no distinct P waves, fibrillatory baseline) "
        "producing an irregularly irregular ventricular response."
    ),
    ArrhythmiaClass.AFL: (
        "Macro-reentrant atrial circuit generating sawtooth flutter waves at ~300 bpm. "
        "Ventricular rate is typically a regular fraction (e.g., 2:1 = 150 bpm)."
    ),
    ArrhythmiaClass.SVT: (
        "Narrow-complex tachycardia (rate 150–250 bpm) originating above or within the "
        "AV node; P waves absent or retrograde; abrupt onset and termination."
    ),
    ArrhythmiaClass.PAC: (
        "Ectopic atrial beat firing before the next expected sinus beat; "
        "P wave morphology differs from sinus; usually followed by a narrow QRS."
    ),
    ArrhythmiaClass.PVC: (
        "Ectopic ventricular beat with wide, bizarre QRS and no preceding P wave; "
        "followed by a compensatory pause."
    ),
    ArrhythmiaClass.VT: (
        "≥3 consecutive wide-complex beats (≥120 ms) at rate > 100 bpm originating "
        "in the ventricles; hemodynamically significant; may degenerate to VF."
    ),
    ArrhythmiaClass.VF: (
        "Chaotic, disorganized ventricular electrical activity; no discernible QRS, "
        "P, or T waves; results in cardiac arrest — requires immediate defibrillation."
    ),
    ArrhythmiaClass.ASYS: (
        "Absence of cardiac electrical activity (flat line); requires CPR and evaluation "
        "for reversible causes (Hs and Ts)."
    ),
}

# ---------------------------------------------------------------------------
# Classification granularity
# ---------------------------------------------------------------------------

# Beat-level classes: classified per individual beat (PAC, PVC, NSR background)
BEAT_LEVEL: frozenset[str] = frozenset({
    ArrhythmiaClass.NSR,
    ArrhythmiaClass.PAC,
    ArrhythmiaClass.PVC,
})

# Strip-level classes: classified over a rhythm window (≥ 5–10 seconds)
STRIP_LEVEL: frozenset[str] = frozenset({
    ArrhythmiaClass.NSR,
    ArrhythmiaClass.SB,
    ArrhythmiaClass.ST,
    ArrhythmiaClass.AF,
    ArrhythmiaClass.AFL,
    ArrhythmiaClass.SVT,
    ArrhythmiaClass.VT,
    ArrhythmiaClass.VF,
    ArrhythmiaClass.ASYS,
})

ALL_CLASSES: list[str] = [c.value for c in ArrhythmiaClass]
