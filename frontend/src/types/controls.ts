import type { Timestamped } from "./common";
import type { Requirement } from "./frameworks";

export type ControlStatus =
  | "not_implemented"
  | "partial"
  | "implemented"
  | "not_applicable";

export type CoverageLevel = "full" | "partial";

export interface MappedRequirement extends Requirement {
  coverage_level: CoverageLevel;
}

export interface Control extends Timestamped {
  workspace_id: string;
  ref: string;
  name: string;
  description: string;
  category: string;
  owner: string;
  status: ControlStatus;
  implementation_notes: string;
  requirements_satisfied_count: number;
  frameworks_touched: number;
  framework_breakdown: Record<string, number>;
  risks_count: number;
  evidence_count: number;
}

export interface ControlDetail extends Control {
  requirements: MappedRequirement[];
  risks: Array<{
    id: string;
    ref: string;
    title: string;
    inherent_score: number;
    residual_score: number;
  }>;
  evidence: Array<{
    id: string;
    title: string;
    status: string;
    source_type: string;
    web_view_link?: string | null;
  }>;
}

export interface ControlCreate {
  ref: string;
  name: string;
  description?: string;
  category?: string;
  owner?: string;
  status?: ControlStatus;
  implementation_notes?: string;
}

export interface ControlUpdate {
  ref?: string;
  name?: string;
  description?: string;
  category?: string;
  owner?: string;
  status?: ControlStatus;
  implementation_notes?: string;
}

export interface RequirementMappingItem {
  requirement_id: string;
  coverage_level: CoverageLevel;
}

export interface RequirementMappingSet {
  items: RequirementMappingItem[];
}
