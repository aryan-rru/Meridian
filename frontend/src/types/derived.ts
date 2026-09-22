export interface CoverageTotals {
  covered: number;
  partial: number;
  gap: number;
  total_requirements: number;
  coverage_percent: number;
}

export interface FrameworkCoverage {
  framework_key: string;
  framework_name: string;
  framework_color: string;
  covered: number;
  partial: number;
  gap: number;
  total: number;
  coverage_percent: number;
  categories: Array<{
    category: string;
    covered: number;
    partial: number;
    gap: number;
    total: number;
    coverage_percent: number;
  }>;
}

export interface CoverageRead {
  frameworks: FrameworkCoverage[];
  totals: CoverageTotals;
}

export interface GapItem {
  requirement_id: string;
  framework_key: string;
  framework_name: string;
  code: string;
  title: string;
  category: string;
  status: "gap" | "partial";
  mapped_controls: Array<{
    id: string;
    ref: string;
    name: string;
    status: string;
    coverage_level: string;
  }>;
  resolution_hint: string;
}

export interface GapsRead {
  items: GapItem[];
  gap_count: number;
  partial_count: number;
}

export interface CrosswalkColumn {
  requirement_id: string;
  code: string;
  title: string;
  category: string;
}

export interface CrosswalkColumnGroup {
  framework_key: string;
  framework_name: string;
  framework_color?: string;
  color?: string;
  columns?: CrosswalkColumn[];
  requirements?: Array<CrosswalkColumn & { mapped_control_count?: number }>;
}

export interface CrosswalkRow {
  control_id: string;
  ref: string;
  name: string;
  category: string;
  status: string;
  requirements_satisfied_count: number;
  frameworks_touched: number;
  framework_breakdown: Record<string, number>;
  cells: Record<string, { coverage_level: "full" | "partial" } | null>;
}

export interface CrosswalkRead {
  column_groups: CrosswalkColumnGroup[];
  rows: CrosswalkRow[];
  summary: {
    total_controls?: number;
    total_requirements?: number;
    total_mappings?: number;
    average_leverage?: number;
    control_count?: number;
    requirement_count?: number;
    mapping_count?: number;
    average_requirements_per_control?: number;
  };
}

export interface RemediationItem {
  control_id: string;
  ref: string;
  name: string;
  category: string;
  status: string;
  priority_score?: number;
  priority?: number;
  risk_leverage: number;
  weighted_risk_leverage?: number;
  weighted_leverage?: number;
  requirement_leverage: number;
  risks: Array<{
    id?: string;
    risk_id?: string;
    ref: string;
    title: string;
    inherent_score: number;
  }>;
  requirements: Array<{
    id?: string;
    requirement_id?: string;
    framework_key: string;
    code: string;
    title: string;
  }>;
}

export interface RemediationRead {
  items: RemediationItem[];
  weights: { W_RISK: number; W_REQ: number };
  candidate_count: number;
}

export interface HeatmapCellRisk {
  id: string;
  ref: string;
  title: string;
  inherent_score: number;
  residual_score: number;
  assurance_flag?: string | null;
}

export interface HeatmapCell {
  likelihood: number;
  impact: number;
  score: number;
  band_name: string;
  band_color: string;
  count: number;
  risks: HeatmapCellRisk[];
}

export interface HeatmapRow {
  likelihood: number;
  likelihood_label: string;
  cells: HeatmapCell[];
}

export interface HeatmapRead {
  basis: "inherent" | "residual";
  matrix_size: number;
  rows: HeatmapRow[];
  impact_labels: Array<{ value: number; label: string }>;
  likelihood_labels: Array<{ value: number; label: string }>;
  total_risks: number;
}

export interface TraceabilityRequirement {
  requirement_id: string;
  code: string;
  title: string;
  category: string;
  coverage_level: string;
  framework: {
    framework_key: string;
    framework_name: string;
    color: string;
  };
}

export interface TraceabilityControl {
  control_id: string;
  ref: string;
  name: string;
  status: string;
  category: string;
  owner: string;
  evidence_count: number;
  requirements_satisfied_count: number;
  requirements: TraceabilityRequirement[];
}

export interface TraceabilityRead {
  risk: {
    id: string;
    ref: string;
    title: string;
    description: string;
    category: string;
    owner: string;
    status: string;
    treatment: string;
    inherent_score: number;
    inherent_band: { name: string; color: string; index?: number };
    residual_score: number;
    residual_band: { name: string; color: string; index?: number };
  };
  controls: TraceabilityControl[];
  assurance: {
    supporting_count: number;
    implemented_count: number;
    partial_count: number;
    not_implemented_count?: number;
    not_applicable_count?: number;
    weakest_status: string | null;
    claims_improvement?: boolean;
    flag: string | null;
    message: string | null;
  };
  aggregate: {
    control_count: number;
    implemented_control_count: number;
    distinct_requirement_count: number;
    frameworks_touched: number;
    frameworks: Array<{
      framework_key: string;
      framework_name: string;
      color: string;
      requirement_count: number;
    }>;
    weakest_control_status: string | null;
    total_evidence_count: number;
  };
}

export interface DashboardSummary {
  controls: {
    total: number;
    by_status: Record<string, number>;
    implemented_percent: number;
  };
  coverage: {
    totals: CoverageTotals;
    frameworks: Array<{
      framework_key: string;
      framework_name: string;
      color: string;
      coverage_percent: number;
      covered_count: number;
      partial_count: number;
      gap_count: number;
      total_requirements: number;
    }>;
  };
  gaps: {
    gap_count: number;
    partial_count: number;
    top_gaps: Array<{
      code: string;
      framework_key: string;
      title: string;
      status: string;
    }>;
  };
  risks: {
    total: number;
    open: number;
    unsupported_residual_count: number;
    top_by_residual: Array<{
      id: string;
      ref: string;
      title: string;
      residual_score: number;
      residual_band: { name: string; color: string; index: number };
      assurance: { flag: string | null };
    }>;
    unsupported_residual: Array<{
      id: string;
      ref: string;
      title: string;
    }>;
  };
  remediation: {
    top_items: RemediationItem[];
    candidate_count: number;
  };
  evidence: {
    total: number;
    by_status: Record<string, number>;
  };
  leverage: Record<string, number>;
}
