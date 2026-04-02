/**
 * Canonical arrhythmia classes for the EKG Trainer.
 *
 * Mirrors python/arrhythmia/constants.py — keep in sync when adding classes.
 */

// ---------------------------------------------------------------------------
// Enum
// ---------------------------------------------------------------------------

export const ArrhythmiaClass = {
  NSR:  "NSR",   // Normal Sinus Rhythm
  SB:   "SB",    // Sinus Bradycardia
  ST:   "ST",    // Sinus Tachycardia
  AF:   "AF",    // Atrial Fibrillation
  AFL:  "AFL",   // Atrial Flutter
  SVT:  "SVT",   // Supraventricular Tachycardia
  PAC:  "PAC",   // Premature Atrial Contraction
  PVC:  "PVC",   // Premature Ventricular Contraction
  VT:   "VT",    // Ventricular Tachycardia
  VF:   "VF",    // Ventricular Fibrillation
  ASYS: "ASYS",  // Asystole
} as const;

export type ArrhythmiaClassKey = keyof typeof ArrhythmiaClass;
export type ArrhythmiaClassValue = (typeof ArrhythmiaClass)[ArrhythmiaClassKey];

export const ALL_ARRHYTHMIA_CLASSES: ArrhythmiaClassValue[] = Object.values(ArrhythmiaClass);

// ---------------------------------------------------------------------------
// Display names
// ---------------------------------------------------------------------------

export const ARRHYTHMIA_DISPLAY_NAMES: Record<ArrhythmiaClassValue, string> = {
  NSR:  "Normal Sinus Rhythm",
  SB:   "Sinus Bradycardia",
  ST:   "Sinus Tachycardia",
  AF:   "Atrial Fibrillation",
  AFL:  "Atrial Flutter",
  SVT:  "Supraventricular Tachycardia",
  PAC:  "Premature Atrial Contraction",
  PVC:  "Premature Ventricular Contraction",
  VT:   "Ventricular Tachycardia",
  VF:   "Ventricular Fibrillation",
  ASYS: "Asystole",
};

// ---------------------------------------------------------------------------
// UI styles
// Tailwind classes + hex fallbacks for non-Tailwind contexts.
// ---------------------------------------------------------------------------

export interface ArrhythmiaStyle {
  /** Tailwind text color class */
  textClass: string;
  /** Tailwind background color class */
  bgClass: string;
  /** Hex color for the label text */
  hex: string;
  /** Hex background color */
  bgHex: string;
}

export const ARRHYTHMIA_STYLES: Record<ArrhythmiaClassValue, ArrhythmiaStyle> = {
  NSR:  { textClass: "text-green-600",  bgClass: "bg-green-50",  hex: "#16a34a", bgHex: "#dcfce7" },
  SB:   { textClass: "text-yellow-600", bgClass: "bg-yellow-50", hex: "#ca8a04", bgHex: "#fef9c3" },
  ST:   { textClass: "text-orange-500", bgClass: "bg-orange-50", hex: "#f97316", bgHex: "#ffedd5" },
  AF:   { textClass: "text-red-500",    bgClass: "bg-red-50",    hex: "#ef4444", bgHex: "#fee2e2" },
  AFL:  { textClass: "text-red-400",    bgClass: "bg-red-50",    hex: "#f87171", bgHex: "#fee2e2" },
  SVT:  { textClass: "text-pink-500",   bgClass: "bg-pink-50",   hex: "#ec4899", bgHex: "#fce7f3" },
  PAC:  { textClass: "text-blue-500",   bgClass: "bg-blue-50",   hex: "#3b82f6", bgHex: "#dbeafe" },
  PVC:  { textClass: "text-purple-600", bgClass: "bg-purple-50", hex: "#9333ea", bgHex: "#f3e8ff" },
  VT:   { textClass: "text-red-700",    bgClass: "bg-red-100",   hex: "#b91c1c", bgHex: "#fee2e2" },
  VF:   { textClass: "text-red-900",    bgClass: "bg-red-200",   hex: "#7f1d1d", bgHex: "#fee2e2" },
  ASYS: { textClass: "text-gray-700",   bgClass: "bg-gray-100",  hex: "#374151", bgHex: "#f3f4f6" },
};

// ---------------------------------------------------------------------------
// Short clinical explanations
// ---------------------------------------------------------------------------

export const ARRHYTHMIA_EXPLANATIONS: Record<ArrhythmiaClassValue, string> = {
  NSR: "Regular rhythm originating from the sinoatrial node at 60–100 bpm. P waves precede every QRS; PR interval 120–200 ms.",
  SB:  "Sinus rhythm with rate < 60 bpm. Normal P-QRS relationship preserved; can be physiologic (athletes) or pathologic.",
  ST:  "Sinus rhythm with rate > 100 bpm. Normal P-QRS relationship; usually a secondary response to fever, pain, hypovolemia, or anxiety.",
  AF:  "Disorganized atrial activity (no distinct P waves, fibrillatory baseline) producing an irregularly irregular ventricular response.",
  AFL: "Macro-reentrant atrial circuit generating sawtooth flutter waves at ~300 bpm. Ventricular rate is typically a regular fraction (e.g., 2:1 = 150 bpm).",
  SVT: "Narrow-complex tachycardia (rate 150–250 bpm) originating above or within the AV node; P waves absent or retrograde; abrupt onset and termination.",
  PAC: "Ectopic atrial beat firing before the next expected sinus beat; P wave morphology differs from sinus; usually followed by a narrow QRS.",
  PVC: "Ectopic ventricular beat with wide, bizarre QRS and no preceding P wave; followed by a compensatory pause.",
  VT:  "≥3 consecutive wide-complex beats (≥120 ms) at rate > 100 bpm originating in the ventricles; may degenerate to VF.",
  VF:  "Chaotic, disorganized ventricular electrical activity; no discernible QRS, P, or T waves; requires immediate defibrillation.",
  ASYS: "Absence of cardiac electrical activity (flat line); requires CPR and evaluation for reversible causes (Hs and Ts).",
};

// ---------------------------------------------------------------------------
// Classification granularity
// ---------------------------------------------------------------------------

/** Classes classified at the individual beat level (PAC/PVC detection) */
export const BEAT_LEVEL_CLASSES: ReadonlySet<ArrhythmiaClassValue> = new Set([
  ArrhythmiaClass.NSR,
  ArrhythmiaClass.PAC,
  ArrhythmiaClass.PVC,
]);

/** Classes classified at the rhythm strip level (≥ 5–10 seconds) */
export const STRIP_LEVEL_CLASSES: ReadonlySet<ArrhythmiaClassValue> = new Set([
  ArrhythmiaClass.NSR,
  ArrhythmiaClass.SB,
  ArrhythmiaClass.ST,
  ArrhythmiaClass.AF,
  ArrhythmiaClass.AFL,
  ArrhythmiaClass.SVT,
  ArrhythmiaClass.VT,
  ArrhythmiaClass.VF,
  ArrhythmiaClass.ASYS,
]);

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------

/** Returns true if the given string is a known ArrhythmiaClassValue */
export function isKnownArrhythmia(label: string): label is ArrhythmiaClassValue {
  return label in ARRHYTHMIA_DISPLAY_NAMES;
}

/** Returns the display name for a label, or the raw label if unknown */
export function getDisplayName(label: string): string {
  return isKnownArrhythmia(label) ? ARRHYTHMIA_DISPLAY_NAMES[label] : label;
}

/** Returns the style for a label, defaulting to a neutral gray style */
export function getStyle(label: string): ArrhythmiaStyle {
  if (isKnownArrhythmia(label)) return ARRHYTHMIA_STYLES[label];
  return { textClass: "text-gray-500", bgClass: "bg-gray-50", hex: "#6b7280", bgHex: "#f9fafb" };
}
