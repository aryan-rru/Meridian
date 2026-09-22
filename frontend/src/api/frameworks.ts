import { api } from "./client";
import type { Framework, Requirement } from "../types";

export interface RequirementFilterParams {
  framework?: string;
  category?: string;
  q?: string;
}

export const frameworksApi = {
  /**
   * List all security frameworks (ISO 27001, SOC 2, NIST CSF).
   */
  listFrameworks: () => api.get<Framework[]>("/frameworks"),

  /**
   * List requirements with optional framework filter, category filter, or search query.
   */
  listRequirements: (params?: RequirementFilterParams) =>
    api.get<Requirement[]>("/requirements", params as Record<string, string>),
};
