export interface RateAnalysis {
  bpm: number;
  rr_intervals_ms: number[];
  category: "bradycardia" | "normal" | "tachycardia";
  method: string;
  confidence: number;
}

export interface RhythmAnalysis {
  regularity: "regular" | "regularly_irregular" | "irregularly_irregular";
  confidence: number;
}

export interface PWaveAnalysis {
  present: boolean;
  morphology: string | null;
  ratio: string | null;
  confidence: number;
}

export interface PRIntervalAnalysis {
  ms: number | null;
  measured_beats: number[];
  normal: boolean | null;
  fixed: boolean | null;
  confidence: number;
}

export interface QRSAnalysis {
  duration_ms: number | null;
  measured_beats_ms: number[];
  wide: boolean;
  morphology: string | null;
  confidence: number;
}

export interface STSegmentAnalysis {
  elevation: boolean;
  depression: boolean;
  details: string | null;
  confidence: number;
}

export interface TWaveAnalysis {
  morphology: string | null;
  confidence: number;
}

export interface QTcAnalysis {
  ms: number | null;
  measured_qt_ms: number[];
  prolonged: boolean | null;
  confidence: number;
}

/**
 * Result of the PhysioNet-compatible signal pipeline pre-classification.
 * Included in the API response alongside the Claude interpretation.
 */
export interface PipelineClassification {
  /** Canonical arrhythmia label (e.g. "AF", "NSR") */
  primary_rhythm: string;
  /** Human-readable display name */
  display_name: string;
  /** Strip-level label before physiologic constraint enforcement */
  strip_label: string;
  /** Classifier confidence in [0, 1] */
  confidence: number;
  /** Per-beat labels from beat model (up to 20) */
  beat_labels: string[];
  /** Whether a deep learning model was used (vs. rule-based) */
  used_deep_learning: boolean;
  /** Notes / warnings from the pipeline */
  notes: string[];
  /** Present when the pipeline threw an error */
  error?: string;
}

export interface EKGAnalysisResult {
  rate: RateAnalysis;
  rhythm: RhythmAnalysis;
  p_waves: PWaveAnalysis;
  pr_interval: PRIntervalAnalysis;
  qrs: QRSAnalysis;
  st_segment: STSegmentAnalysis;
  t_waves: TWaveAnalysis;
  qtc: QTcAnalysis;
  primary_rhythm: string;
  overall_confidence: number;
  differentials: string[];
  explanation: string;
  image_quality: "good" | "fair" | "poor";
  caveats: string | null;
  /** Signal pipeline pre-classification (present for user uploads, absent for pre-computed) */
  pipeline_classification?: PipelineClassification | null;
}

export interface AnalyzeRequest {
  /** Required when caseId is not provided (or not found in pre-computed data). */
  imageBase64?: string;
  mediaType?: "image/jpeg" | "image/png" | "image/gif" | "image/webp";
  /** When provided and found in pre-computed measurements, skips image upload entirely. */
  caseId?: string;
}

export interface AnalyzeResponse {
  success: true;
  result: EKGAnalysisResult;
}

export interface AnalyzeErrorResponse {
  success: false;
  error: string;
}
