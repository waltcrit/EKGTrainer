export type RhythmCategory =
  | "sinus"
  | "atrial"
  | "supraventricular"
  | "av_block"
  | "bundle_branch"
  | "junctional"
  | "ventricular"
  | "stemi"
  | "nstemi"
  | "pe_strain";

export interface EKGCase {
  id: string;
  rhythm: string;
  category: RhythmCategory;
  difficulty: 1 | 2 | 3 | 4;   // 1 = easiest, 4 = hardest
  imagePath: string;
  rate: number | null;
  regularity: "regular" | "regularly_irregular" | "irregularly_irregular" | "chaotic" | "none";
  keyFeatures: string[];
  teaching: string;
}

export const CATEGORY_LABELS: Record<RhythmCategory, string> = {
  sinus:             "Sinus Rhythms",
  atrial:            "Atrial",
  supraventricular:  "Supraventricular",
  av_block:          "AV Blocks",
  bundle_branch:     "Bundle Branch Blocks",
  junctional:        "Junctional / Escape",
  ventricular:       "Ventricular",
  stemi:             "STEMI",
  nstemi:            "NSTEMI / ACS",
  pe_strain:         "PE & Strain Patterns",
};

export const DIFFICULTY_LABELS: Record<number, string> = {
  1: "Foundational",
  2: "Intermediate",
  3: "Advanced",
  4: "Expert",
};
