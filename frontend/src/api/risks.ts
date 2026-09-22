import { api } from "./client";
import type {
  Risk,
  RiskCreate,
  RiskUpdate,
  HeatmapRead,
  TraceabilityRead,
  MessageResponse,
} from "../types";

export interface RiskFilterParams {
  status?: string;
  band?: string;
  category?: string;
  q?: string;
}

export const risksApi = {
  /**
   * List risks with computed inherent/residual scores, bands, and assurance check.
   */
  list: (params?: RiskFilterParams) =>
    api.get<Risk[]>("/risks", params as Record<string, string>),

  /**
   * 5x5 Likelihood x Impact distribution with risk groupings.
   */
  getHeatmap: (basis: "inherent" | "residual" = "residual") =>
    api.get<HeatmapRead>("/risks/heatmap", { basis }),

  /**
   * Create a new risk in the current workspace.
   */
  create: (payload: RiskCreate) =>
    api.post<Risk>("/risks", payload),

  /**
   * Get single risk detail.
   */
  get: (id: string) =>
    api.get<Risk>(`/risks/${id}`),

  /**
   * Update risk fields or scores.
   */
  update: (id: string, payload: RiskUpdate) =>
    api.patch<Risk>(`/risks/${id}`, payload),

  /**
   * Delete a risk.
   */
  delete: (id: string) =>
    api.delete<MessageResponse>(`/risks/${id}`),

  /**
   * Set mitigating controls for this risk.
   */
  setControls: (id: string, controlIds: string[]) =>
    api.put<Risk>(`/risks/${id}/controls`, { control_ids: controlIds }),

  /**
   * End-to-end traceability tree: Risk -> Controls -> Requirements -> Frameworks.
   */
  getTraceability: (id: string) =>
    api.get<TraceabilityRead>(`/risks/${id}/traceability`),
};
