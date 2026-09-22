import type { Timestamped } from "./common";

export type EvidenceSource = "drive_file" | "google_sheet" | "upload" | "url";
export type EvidenceStatus = "current" | "stale" | "missing";

export interface Evidence extends Timestamped {
  workspace_id: string;
  control_id: string;
  control_ref?: string | null;
  control_name?: string | null;
  title: string;
  description: string;
  source_type: EvidenceSource;
  drive_file_id?: string | null;
  drive_file_name: string;
  mime_type: string;
  web_view_link?: string | null;
  url?: string | null;
  collected_at?: string | null;
  valid_until?: string | null;
  status: EvidenceStatus;
  extracted_data?: Record<string, unknown> | null;
  extracted_at?: string | null;
}

export interface EvidenceLinkCreate {
  control_id: string;
  drive_file_id?: string | null;
  title?: string | null;
  description?: string;
  source_type?: EvidenceSource;
  url?: string | null;
  valid_until?: string | null;
}

export interface EvidenceUpdate {
  title?: string | null;
  description?: string | null;
  valid_until?: string | null;
}

export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  webViewLink?: string | null;
  iconLink?: string | null;
  modifiedTime?: string | null;
  size?: string | null;
}

export interface DriveFileList {
  files: DriveFile[];
  scope_limited: boolean;
}

export interface ExtractionResult {
  evidence_id: string;
  status: string;
  extracted_at?: string | null;
  extracted_data?: Record<string, unknown> | null;
  message: string;
}
