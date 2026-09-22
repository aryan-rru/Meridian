export type ScoreMethod = "multiply" | "add" | "weighted";

export interface RiskBand {
  name: string;
  min: number;
  max: number;
  color: string;
}

export interface ScoringConfig {
  matrix_size: number;
  score_method: ScoreMethod;
  weights: { wL: number; wI: number };
  likelihood_labels: Record<string, string>;
  impact_labels: Record<string, string>;
  risk_bands: RiskBand[];
  remediation_weights: { W_RISK: number; W_REQ: number };
  evidence_stale_after_days: number;
  min_possible_score: number;
  max_possible_score: number;
}

export interface ScoringConfigUpdate {
  matrix_size?: number;
  score_method?: ScoreMethod;
  weights?: { wL: number; wI: number };
  likelihood_labels?: Record<string, string>;
  impact_labels?: Record<string, string>;
  risk_bands?: RiskBand[];
  remediation_weights?: { W_RISK: number; W_REQ: number };
  evidence_stale_after_days?: number;
}

export interface ImportError {
  sheet: string;
  row?: number | null;
  message: string;
}

export interface ImportSummary {
  created: number;
  updated: number;
  skipped: number;
  errors: ImportError[];
  sheets: Record<string, Record<string, number>>;
}

export interface DriveExportResult {
  file_id: string;
  name: string;
  web_view_link?: string | null;
  message: string;
}
