import { api } from "./client";
import type { MeResponse, MessageResponse, DevLoginRequest } from "../types";
import { buildApiUrl } from "../config/env";

export const authApi = {
  /**
   * Fetch current session info: user, workspaces, current workspace, and Google status.
   */
  getMe: () => api.get<MeResponse>("/auth/me"),

  /**
   * Log in using local dev bypass (only active when DEV_LOGIN_ENABLED=true).
   */
  devLogin: (payload: DevLoginRequest = {}) =>
    api.post<MeResponse>("/auth/dev-login", payload),

  /**
   * Sign out and clear the session cookie.
   */
  logout: () => api.post<MessageResponse>("/auth/logout"),

  /**
   * Get the full URL to initiate Google OAuth login flow.
   */
  getGoogleLoginUrl: () => buildApiUrl("/auth/google/login"),
};
