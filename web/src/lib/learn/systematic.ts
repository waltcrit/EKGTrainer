/**
 * Canonical 10-step systematic EKG reading method.
 * Used in the "Systematic Approach" lesson and in the live Trainer checklist.
 */

export interface SystematicStep {
  id: string;
  title: string;
  description: string;
  subpoints?: string[];
}

export const SYSTEMATIC_STEPS: SystematicStep[] = [
  {
    id: "basics",
    title: "Confirm Basics",
    description: "Verify patient identity, clinical context, and technical quality.",
    subpoints: [
      "Correct patient name and date",
      "Leads properly placed (no reversals)",
      "Adequate signal (10 mm/mV calibration, 25 mm/s paper speed)",
      "Minimize artifact before interpreting",
    ],
  },
  {
    id: "rate",
    title: "Rate",
    description: "Calculate ventricular rate (and atrial rate if different).",
    subpoints: [
      "Regular rhythm: 300 ÷ number of large boxes between R–R",
      "Irregular rhythm: count QRS complexes in 10-second strip × 6",
      "Normal: 60–100 bpm; Brady < 60; Tachy > 100",
    ],
  },
  {
    id: "rhythm",
    title: "Rhythm",
    description: "Determine if the rhythm is regular, regularly irregular, or irregularly irregular.",
    subpoints: [
      "March out R–R intervals with calipers",
      "Note: regularly irregular suggests a pattern (e.g., bigeminy, Wenckebach)",
      "Chaotic/irregularly irregular → think atrial fibrillation",
    ],
  },
  {
    id: "p_waves",
    title: "P Waves",
    description: "Assess presence, morphology, axis, and relationship to QRS.",
    subpoints: [
      "Is a P wave present before every QRS?",
      "Are all P waves identical in a given lead?",
      "Upright in I and II → normal sinus origin",
      "P:QRS ratio — more P waves than QRS = high-degree block",
    ],
  },
  {
    id: "pr_interval",
    title: "PR Interval",
    description: "Measure from start of P to start of QRS; normal 120–200 ms.",
    subpoints: [
      "Short PR (< 120 ms): pre-excitation, junctional, or posterior atrial focus",
      "Long PR (> 200 ms): 1st-degree AV block",
      "Progressively lengthening PR → Mobitz I (Wenckebach)",
      "Fixed PR with dropped beats → Mobitz II",
    ],
  },
  {
    id: "qrs",
    title: "QRS Complex",
    description: "Measure duration; assess morphology and axis.",
    subpoints: [
      "Normal duration ≤ 120 ms (3 small boxes)",
      "Wide QRS (> 120 ms): BBB, aberrancy, ventricular rhythm, hyperkalemia",
      "Delta waves → pre-excitation (WPW)",
      "Axis: normal −30° to +90°; LAD or RAD suggests pathology",
    ],
  },
  {
    id: "st_t",
    title: "ST Segments & T Waves",
    description: "Inspect for elevation, depression, or T-wave abnormalities.",
    subpoints: [
      "ST elevation ≥ 1 mm in ≥2 contiguous leads → STEMI territory",
      "ST depression / T-wave inversions → ischemia, LVH strain, BBB",
      "Diffuse concave ST elevation + PR depression → pericarditis",
      "Peaked T waves → hyperkalemia; flattened / inverted → multiple causes",
    ],
  },
  {
    id: "qt",
    title: "QT Interval",
    description: "Measure QT and calculate QTc; normal QTc ≤ 440 ms (men) / ≤ 460 ms (women).",
    subpoints: [
      "Measure from start of QRS to end of T wave",
      "Bazett formula: QTc = QT / √(R–R in seconds)",
      "Prolonged QTc → risk of torsades de pointes",
      "Short QTc (< 340 ms): hypercalcemia, digitalis, short QT syndrome",
    ],
  },
  {
    id: "compare",
    title: "Compare with Prior",
    description: "Always compare to the most recent previous EKG when available.",
    subpoints: [
      "New ST changes are more significant than chronic ones",
      "New BBB or axis shift can indicate acute pathology",
      "Rate or rhythm change from baseline may explain symptoms",
    ],
  },
  {
    id: "synthesize",
    title: "Synthesize",
    description: "Name the rhythm, state key findings, and correlate with clinical context.",
    subpoints: [
      "State the primary rhythm (e.g., 'Sinus tachycardia at 110 bpm')",
      "List additional findings in order of clinical urgency",
      "Correlate with symptoms, vitals, and history",
      "State a plan: compare, repeat, treat, or consult",
    ],
  },
];

export type StepId =
  | "basics"
  | "rate"
  | "rhythm"
  | "p_waves"
  | "pr_interval"
  | "qrs"
  | "st_t"
  | "qt"
  | "compare"
  | "synthesize";
