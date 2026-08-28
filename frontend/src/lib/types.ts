export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Confidence = "LOW" | "MEDIUM" | "HIGH";

export interface Issue {
  type: string;
  detected: boolean;
  severity: Severity;
  severity_value: number;
  confidence: number;
  ml_probability: number;
  cv_severity: number;
  agreement: number;
  evidence: Record<string, number>;
}

export interface ForensicCard {
  issue: string;
  signal: string;
  observed: string;
  model_expectation: string;
  assessment: string;
  confidence: number;
}

export interface EvidenceCard {
  issue: string;
  severity: string;
  confidence: number;
  explanation: string;
  statistic: string;
}

export interface Explainability {
  primary_issue: string | null;
  heatmap: string | null;
  heatmap_method: string;
  problem_regions: string | null;
  problem_method: string;
  forensics: ForensicCard[];
  evidence_cards: EvidenceCard[];
  narrative: string;
}

export interface AnalysisResult {
  id: string;
  created_at: string;
  filename: string;
  format: string;
  image: {
    width: number; height: number; channels: number;
    megapixels: number; aspect_ratio: number; file_size_kb: number;
  };
  quality_score: number;
  quality_label: string;
  quality_class: string;
  class_probabilities: Record<string, number>;
  overall_confidence: Confidence;
  overall_confidence_value: number;
  review_recommended: boolean;
  review_reasons: string[];
  issues: Issue[];
  detected_issue_types: string[];
  dimensions: Record<string, number>;
  statistics: Record<string, number | null>;
  signal_agreement: {
    overall: string; value: number; per_issue: Record<string, number>;
  };
  anomaly: {
    // `score` is an uncalibrated [0,1] anomaly score (monotonic in z_score),
    // not a probability. See docs/model.md.
    detected: boolean; label: string; score: number;
    z_score: number; recon_error: number;
  };
  explainability: Explainability;
  model_info: Record<string, unknown>;
  analysis_time_ms: number;
}

export interface HistoryItem {
  id: string;
  created_at: string;
  filename: string;
  quality_score: number;
  quality_label: string;
  quality_class: string;
  overall_confidence: Confidence;
  review_recommended: boolean;
  primary_issue: string | null;
  thumbnail_url: string | null;
}

export interface HistoryList {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

// The single-analysis detail response (schemas/history.py: AnalysisDetail).
// Deliberately different from AnalysisResult: media are URLs (not data URLs),
// narrative/forensics are top-level, and `image` omits megapixels/aspect_ratio.
export interface AnalysisDetail {
  id: string;
  created_at: string;
  filename: string;
  format: string;
  image: { width: number; height: number; channels: number; file_size_kb: number };
  quality_score: number;
  quality_label: string;
  quality_class: string;
  overall_confidence: Confidence;
  review_recommended: boolean;
  primary_issue: string | null;
  detected_issues: string[];
  issues: Issue[];
  statistics: Record<string, number | null>;
  dimensions: Record<string, number>;
  signal_agreement: { overall: string; value: number; per_issue: Record<string, number> };
  anomaly: Record<string, number | string | boolean>;
  forensics: ForensicCard[];
  narrative: string;
  thumbnail_url: string | null;
  heatmap_url: string | null;
  problem_regions_url: string | null;
  model_info: Record<string, unknown>;
  analysis_time_ms: number;
}

export interface Statistics {
  total: number;
  average_score: number | null;
  by_label: Record<string, number>;
  review_rate: number;
}

export interface Health {
  status: "healthy" | "degraded";
  model_loaded: boolean;
  anomaly_model_loaded: boolean;
  database: string;
  device: string;
  model: { name: string; version: string };
  version: string;
}

export interface ModelInfo {
  model_name: string;
  model_version: string;
  input_resolution: number;
  quality_classes: string[];
  issue_types: string[];
  framework: string;
  pretrained_backbone: boolean;
  loss_weights: Record<string, number>;
  trained_at: string | null;
  validation_metrics: Record<string, number>;
  device: string;
  calibrated: boolean;
}

export interface DemoSample { key: string; label: string; url: string; }
