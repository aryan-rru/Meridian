import type { Timestamped } from "./common";

export type WorkspaceRole = "owner" | "admin" | "member" | "viewer";

export interface User extends Timestamped {
  email: string;
  name: string;
  picture_url: string | null;
}

export interface Workspace extends Timestamped {
  name: string;
  evidence_folder_id: string | null;
}

export interface WorkspaceMembership {
  workspace: Workspace;
  role: string;
}

export interface GoogleStatus {
  connected: boolean;
  configured: boolean;
  granted_scopes: string[];
  can_browse_drive: boolean;
  can_read_sheets: boolean;
}

export interface MeResponse {
  user: User;
  workspaces: WorkspaceMembership[];
  current_workspace: Workspace | null;
  current_role: string | null;
  google: GoogleStatus;
}

export interface DevLoginRequest {
  email?: string;
}

export interface LoginUrlResponse {
  authorization_url: string;
  state: string;
}

export interface SwitchWorkspaceResponse {
  current_workspace: Workspace;
  role: string;
  workspace_id: string;
}

export interface MemberInvite {
  email: string;
  role?: string;
}

export interface Member extends Timestamped {
  user: User;
  role: string;
}
