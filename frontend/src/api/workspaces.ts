import { api } from "./client";
import type {
  Workspace,
  WorkspaceMembership,
  SwitchWorkspaceResponse,
  Member,
  MemberInvite,
} from "../types";

export const workspacesApi = {
  /**
   * List workspaces the current user belongs to.
   */
  list: () => api.get<WorkspaceMembership[]>("/workspaces"),

  /**
   * Create a new workspace. The creator becomes the owner.
   */
  create: (name: string) => api.post<Workspace>("/workspaces", { name }),

  /**
   * Switch active workspace in the user's session.
   */
  switch: (workspaceId: string) =>
    api.post<SwitchWorkspaceResponse>(`/workspaces/${workspaceId}/switch`),

  /**
   * List members of the specified workspace.
   */
  listMembers: (workspaceId: string) =>
    api.get<Member[]>(`/workspaces/${workspaceId}/members`),

  /**
   * Invite a user to the workspace.
   */
  inviteMember: (workspaceId: string, payload: MemberInvite) =>
    api.post<Member>(`/workspaces/${workspaceId}/members`, payload),
};
