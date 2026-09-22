import { api } from "./client";
import type {
  CrosswalkRead,
  CoverageRead,
  GapsRead,
  RemediationRead,
  DashboardSummary,
} from "../types";

export const derivedApi = {
  /**
   * Crosswalk matrix: Controls x Requirements grouped by framework.
   */
  getCrosswalk: () =>
    api.get<CrosswalkRead>("/crosswalk"),

  /**
   * Coverage report: Per-framework and per-category coverage for the heatmap.
   */
  getCoverage: () =>
    api.get<CoverageRead>("/coverage"),

  /**
   * Gap analysis: Requirements that have gaps or partial coverage, with resolution hints.
   */
  getGaps: () =>
    api.get<GapsRead>("/coverage/gaps"),

  /**
   * Remediation priority ranking: Controls ranked by risk and requirement leverage.
   */
  getRemediation: () =>
    api.get<RemediationRead>("/remediation"),

  /**
   * Dashboard summary: Aggregated metrics across controls, coverage, risks, and evidence.
   */
  getDashboardSummary: () =>
    api.get<DashboardSummary>("/dashboard/summary"),
};
