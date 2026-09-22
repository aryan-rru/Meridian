/**
 * Application environment configuration.
 * Reads Vite environment variables with safe defaults.
 */

export interface AppConfig {
  apiBaseUrl: string;
  googleClientId: string;
  googleApiKey: string;
  isDev: boolean;
}

const rawApiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "/api";

export const config: AppConfig = {
  apiBaseUrl: rawApiBaseUrl.replace(/\/+$/, ""),
  googleClientId: (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) || "",
  googleApiKey: (import.meta.env.VITE_GOOGLE_API_KEY as string | undefined) || "",
  isDev: import.meta.env.DEV,
};

/**
 * Build a full URL from a relative API path.
 * Ensures single slash separation.
 */
export function buildApiUrl(path: string): string {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${config.apiBaseUrl}${cleanPath}`;
}
