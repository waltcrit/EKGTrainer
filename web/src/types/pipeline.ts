import type { PipelineClassification } from "@/types/analysis";

export type ImageMediaType = "image/jpeg" | "image/png" | "image/gif" | "image/webp";

export interface Image {
  base64: string;
  mediaType: ImageMediaType;
}

export type RhythmRegularity = "regular" | "regularly_irregular" | "irregularly_irregular";

export interface SignalMeasurements {
  r_peaks?: number[];
  rr_intervals_ms?: number[];
  heart_rate_bpm?: number;
  regularity?: RhythmRegularity | string;
  p_waves_present?: boolean;
  pr_interval_ms?: number | null;
  qrs_duration_ms?: number | null;
  qrs_wide?: boolean;
  qt_ms?: number | null;
  qtc_ms?: number | null;
  qtc_prolonged?: boolean | null;
  st?: Record<string, { elevation?: boolean; depression?: boolean; mean_mv?: number }>;
  num_beats?: number;
  rhythm_lead?: string;
  p_peaks?: number[];
  pp_intervals_ms?: number[];
}

export interface PipelineData {
  measurements: Record<string, unknown>;
  claude_prompt: string;
  digitizer_method: string;
  leads_available: string[];
  sampling_rate: number;
  pipeline_classification?: PipelineClassification | null;
}

export interface PythonServiceResult extends PipelineData {
  success: true;
}

/** All signal fields normalized to concrete types — computed once and passed to all downstream functions. */
export interface NormalizedSignal {
  hr: number;
  category: "bradycardia" | "normal" | "tachycardia";
  regularity: RhythmRegularity;
  prMs: number | null;
  qrsMs: number | null;
  qtcMs: number | null;
  qtMs: number | null;
  qtcProlonged: boolean | null;
  qrsWide: boolean;
  pPresent: boolean;
  elevatedLeads: string[];
  depressedLeads: string[];
  stDetails: string | null;
  rr: number[];
  ppIntervals: number[];
  rrIntervals: number[];
  rhythmCode: string;
  rhythmDisplay: string;
  baseConf: number;
  rhythmLead: string;
}
