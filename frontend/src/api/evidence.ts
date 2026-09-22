import { api } from "./client";
import type {
  Evidence,
  EvidenceLinkCreate,
  EvidenceUpdate,
  DriveFileList,
  ExtractionResult,
  MessageResponse,
} from "../types";

export interface DriveListParams {
  q?: string;
  mimeType?: string;
  page_size?: number;
}

export const evidenceApi = {
  /**
   * Search files in the user's Google Drive.
   */
  listDriveFiles: (params?: DriveListParams) =>
    api.get<DriveFileList>("/drive/files", params as Record<string, string | number>),

  /**
   * List evidence records, optionally filtered by control ID.
   */
  listEvidence: (controlId?: string) =>
    api.get<Evidence[]>("/evidence", controlId ? { control_id: controlId } : undefined),

  /**
   * Link an existing Drive file or external URL as evidence for a control.
   */
  linkEvidence: (payload: EvidenceLinkCreate) =>
    api.post<Evidence>("/evidence", payload),

  /**
   * Upload an evidence file directly to Google Drive and link it to a control.
   */
  uploadEvidence: async (
    controlId: string,
    file: File,
    title?: string,
    validUntil?: string
  ): Promise<Evidence> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("control_id", controlId);
    if (title) formData.append("title", title);
    if (validUntil) formData.append("valid_until", validUntil);

    return api.post<Evidence>("/evidence/upload", formData);
  },

  /**
   * Get single evidence detail including extracted sheet data.
   */
  getEvidence: (id: string) =>
    api.get<Evidence>(`/evidence/${id}`),

  /**
   * Update evidence metadata.
   */
  updateEvidence: (id: string, payload: EvidenceUpdate) =>
    api.patch<Evidence>(`/evidence/${id}`, payload),

  /**
   * Delete an evidence link.
   */
  deleteEvidence: (id: string) =>
    api.delete<MessageResponse>(`/evidence/${id}`),

  /**
   * Download and parse Excel/Sheet evidence file to extract summary data.
   */
  extractEvidence: (id: string) =>
    api.post<ExtractionResult>(`/evidence/${id}/extract`),
};
