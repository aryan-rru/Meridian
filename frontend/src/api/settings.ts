import { api } from "./client";
import type { ScoringConfig, ScoringConfigUpdate } from "../types";

export const settingsApi = {
  /**
   * Get current workspace scoring configuration.
   */
  getSettings: () =>
    api.get<ScoringConfig>("/settings"),

  /**
   * Update scoring method, weights, labels, bands, or matrix size.
   * Re-derives all scores across the workspace upon saving.
   */
  updateSettings: (payload: ScoringConfigUpdate) =>
    api.put<ScoringConfig>("/settings", payload),
};
