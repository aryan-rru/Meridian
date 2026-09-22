import { api } from "./client";
import type {
  Control,
  ControlDetail,
  ControlCreate,
  ControlUpdate,
  RequirementMappingSet,
  MessageResponse,
  Evidence,
} from "../types";

export interface ControlFilterParams {
  status?: string;
  category?: string;
  q?: string;
}

export const controlsApi = {
  /**
   * List controls with computed counts (requirements, frameworks, risks, evidence).
   */
  list: (params?: ControlFilterParams) =>
    api.get<Control[]>("/controls", params as Record<string, string>),

  /**
   * Create a new control in the current workspace.
   */
  create: (payload: ControlCreate) =>
    api.post<Control>("/controls", payload),

  /**
   * Get control detail including mapped requirements, mitigated risks, and attached evidence.
   */
  get: (id: string) =>
    api.get<ControlDetail>(`/controls/${id}`),

  /**
   * Update control fields or status.
   */
  update: (id: string, payload: ControlUpdate) =>
    api.patch<Control>(`/controls/${id}`, payload),

  /**
   * Delete a control and cascade its mappings.
   */
  delete: (id: string) =>
    api.delete<MessageResponse>(`/controls/${id}`),

  /**
   * Update requirement mappings (tick boxes) for this control.
   */
  setRequirements: (id: string, payload: RequirementMappingSet) =>
    api.put<ControlDetail>(`/controls/${id}/requirements`, payload),

  /**
   * List evidence records linked to this control.
   */
  getEvidence: (id: string) =>
    api.get<Evidence[]>(`/controls/${id}/evidence`),
};
