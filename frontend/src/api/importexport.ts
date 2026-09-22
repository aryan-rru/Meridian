import { api, apiFetchBlob } from "./client";
import type { ImportSummary, DriveExportResult } from "../types";
import { buildApiUrl } from "../config/env";

export const importExportApi = {
  /**
   * Import multi-sheet Excel workbook to upsert controls, requirements, risks, and mappings.
   */
  importExcel: async (file: File): Promise<ImportSummary> => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post<ImportSummary>("/import/excel", formData);
  },

  /**
   * Get direct URL for downloading the workspace Excel export.
   */
  getExportExcelUrl: () => buildApiUrl("/export/excel"),

  /**
   * Download the multi-sheet Excel export workbook as a Blob.
   */
  downloadExcel: () => apiFetchBlob("/export/excel"),

  /**
   * Generate export workbook and save it directly to user's Google Drive folder.
   */
  exportToDrive: () => api.post<DriveExportResult>("/export/drive"),
};
