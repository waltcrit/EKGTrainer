/**
 * Canonical systematic EKG read — mirrors docs/analysis_steps.md (17 steps).
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
    id: "patient",
    title: "Confirm correct patient",
    description: "Wrong tracing or chart pairing invalidates everything downstream.",
  },
  {
    id: "prior_ekgs",
    title: "Check prior EKGs",
    description: "New change suggests acute pathology; stable change suggests baseline or chronic findings.",
  },
  {
    id: "rate",
    title: "Assess rate",
    description:
      "Fast → tachycardia spectrum, flutter/AF/VT, or physiologic stress; Slow → sinus brady, AV block, meds, metabolic causes.",
  },
  {
    id: "rhythm",
    title: "Assess rhythm",
    description:
      "Regularly irregular vs irregularly irregular narrows AV block patterns, flutter with variable block, AF/MAT, ectopy.",
  },
  {
    id: "p_before_qrs",
    title: "Check P before each QRS",
    description:
      "Missing vs extra vs disconnected P waves — AF, junctional rhythm, AV block, flutter.",
  },
  {
    id: "intervals",
    title: "Measure intervals",
    description:
      "PR long/short, QRS wide/narrow, QT long — AV nodal disease, pre-excitation, BBB/VT/hyperK, torsades risk.",
  },
  {
    id: "p_waves",
    title: "Evaluate P waves",
    description:
      "Abnormal P → atrial enlargement or ectopic atrial rhythm; inverted inferior P → junctional/low-atrial origin.",
  },
  {
    id: "axis",
    title: "Evaluate axis",
    description:
      "LAD/RAD/extreme — bundle hemiblocks, LVH/RVH, infarction, lung disease, lead reversal, severe conduction disease.",
  },
  {
    id: "precordial_progression",
    title: "Check precordial progression",
    description:
      "Poor progression → anterior MI, lead misplacement, LBBB, RVH, COPD, normal variant.",
  },
  {
    id: "st_segments",
    title: "Check ST segments",
    description:
      "Anchor STE/STD at the J-point. STE vs STD — STEMI injury vs ischemia, reciprocal change, digoxin, strain, mimics.",
  },
  {
    id: "t_waves",
    title: "Check T waves",
    description:
      "Inversion, peaked T (hyperK), flat/biphasic — ischemia, strain, BBB, PE, electrolytes, Wellens-type morphology.",
  },
  {
    id: "q_waves",
    title: "Check Q waves",
    description: "Pathologic Q — prior MI/scar, cardiomyopathy, lead misplacement.",
  },
  {
    id: "ischemia_acs",
    title: "Ischemia / ACS patterns",
    description:
      "Cross-lead patterns — Wellens, de Winter, hyperacute MI; modified Sgarbossa (primary) vs classic Sgarbossa, Barcelona; adjunct to guidelines.",
  },
  {
    id: "strain",
    title: "Strain",
    description:
      "LVH strain vs lateral ischemia — ST/T discordant vs concordant ST depression with QRS.",
  },
  {
    id: "pulmonary_pattern",
    title: "Pulmonary disease pattern",
    description:
      "PE (e.g. S1Q3T3, tach, new RBBB/RAD) and chronic lung pattern — RAD, P pulmonale, low voltage, poor progression.",
  },
  {
    id: "pericarditis_vs_mimic",
    title: "Pericarditis vs mimic",
    description:
      "Diffuse STE + Spodick sign vs early repolarization — concave J-point STE, fishhook J.",
  },
  {
    id: "channelopathy_structural",
    title: "Channelopathy / structural",
    description:
      "Brugada type 1 coved — ARVC with epsilon wave (terminal notch V1–V3).",
  },
];

export type StepId =
  | "patient"
  | "prior_ekgs"
  | "rate"
  | "rhythm"
  | "p_before_qrs"
  | "intervals"
  | "p_waves"
  | "axis"
  | "precordial_progression"
  | "st_segments"
  | "t_waves"
  | "q_waves"
  | "ischemia_acs"
  | "strain"
  | "pulmonary_pattern"
  | "pericarditis_vs_mimic"
  | "channelopathy_structural";

/** Same order as `SYSTEMATIC_STEPS` — aligned with the `StepId` union. */
export const SYSTEMATIC_STEP_IDS: StepId[] = SYSTEMATIC_STEPS.map((s) => s.id as StepId);
