import type { Assurance, Band, ControlSummary, Timestamped } from "./common";

export type RiskTreatment = "mitigate" | "accept" | "transfer" | "avoid";
export type RiskStatus = "open" | "monitoring" | "closed";

export interface Risk extends Timestamped {
  ref: string;
  title: string;
  description: string;
  category: string;
  owner: string;
  treatment: RiskTreatment;
  status: RiskStatus;

  inherent_likelihood: number;
  inherent_impact: number;
  residual_likelihood: number;
  residual_impact: number;
  inherent_likelihood_label: string;
  inherent_impact_label: string;
  residual_likelihood_label: string;
  residual_impact_label: string;

  inherent_score: number;
  inherent_band: Band;
  residual_score: number;
  residual_band: Band;
  score_reduction: number;

  assurance: Assurance;
  controls: ControlSummary[];
  control_count: number;
}

export interface RiskCreate {
  ref: string;
  title: string;
  description?: string;
  category?: string;
  owner?: string;
  inherent_likelihood: number;
  inherent_impact: number;
  residual_likelihood: number;
  residual_impact: number;
  treatment?: RiskTreatment;
  status?: RiskStatus;
}

export interface RiskUpdate {
  ref?: string;
  title?: string;
  description?: string;
  category?: string;
  owner?: string;
  inherent_likelihood?: number;
  inherent_impact?: number;
  residual_likelihood?: number;
  residual_impact?: number;
  treatment?: RiskTreatment;
  status?: RiskStatus;
}

export interface RiskControlSet {
  control_ids: string[];
}
