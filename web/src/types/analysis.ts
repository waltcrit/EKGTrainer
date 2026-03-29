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
}

export interface AnalyzeRequest {
  imageBase64: string;
  mediaType: "image/jpeg" | "image/png" | "image/gif" | "image/webp";
}

export interface AnalyzeResponse {
  success: true;
  result: EKGAnalysisResult;
}

export interface AnalyzeErrorResponse {
  success: false;
  error: string;
}
