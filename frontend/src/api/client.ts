import { buildApiUrl } from "../config/env";
import type { ApiProblem } from "../types/common";

export class ApiError extends Error {
  readonly status: number;
  readonly problems?: ApiProblem[];
  readonly raw?: unknown;

  constructor(status: number, message: string, problems?: ApiProblem[], raw?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.problems = problems;
    this.raw = raw;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  params?: Record<string, string | number | boolean | null | undefined>;
  body?: unknown;
}

/**
 * Serialize URL query parameters, filtering out null/undefined values.
 */
function buildQueryString(params?: Record<string, string | number | boolean | null | undefined>): string {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.append(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Parse server error responses into a human-friendly format.
 */
async function extractErrorMessage(response: Response): Promise<{ message: string; problems?: ApiProblem[]; raw?: unknown }> {
  try {
    const data = await response.json();
    if (data && typeof data === "object") {
      // Pydantic validation error shape
      if ("detail" in data) {
        const detail = (data as { detail: unknown }).detail;
        if (typeof detail === "string") {
          return { message: detail, raw: data };
        }
        if (typeof detail === "object" && detail !== null) {
          const detailObj = detail as { message?: string; problems?: ApiProblem[] };
          return {
            message: detailObj.message || "Request validation failed.",
            problems: detailObj.problems,
            raw: data,
          };
        }
      }
      if ("message" in data && typeof (data as { message: unknown }).message === "string") {
        return { message: (data as { message: string }).message, raw: data };
      }
    }
    return { message: `Request failed with status ${response.status}`, raw: data };
  } catch {
    return { message: response.statusText || `Request failed with status ${response.status}` };
  }
}

/**
 * Base fetch function with automatic credentials, headers, and error handling.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { params, headers: customHeaders, body, ...rest } = options;
  const url = `${buildApiUrl(path)}${buildQueryString(params)}`;

  const headers = new Headers(customHeaders);
  let requestBody: BodyInit | null | undefined = undefined;

  if (body !== undefined && body !== null) {
    if (body instanceof FormData || body instanceof Blob) {
      requestBody = body;
    } else {
      requestBody = JSON.stringify(body);
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
    }
  }

  const response = await fetch(url, {
    ...rest,
    headers,
    body: requestBody,
    credentials: "include", // §13 — session cookie authentication
  });

  if (!response.ok) {
    const { message, problems, raw } = await extractErrorMessage(response);
    throw new ApiError(response.status, message, problems, raw);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  // Check content type to see if JSON is returned
  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }

  return (await response.text()) as unknown as T;
}

export async function apiFetchBlob(path: string, options: RequestOptions = {}): Promise<{ blob: Blob; filename?: string }> {
  const { params, headers: customHeaders, body, ...rest } = options;
  const url = `${buildApiUrl(path)}${buildQueryString(params)}`;

  let requestBody: BodyInit | null | undefined = undefined;
  if (body !== undefined && body !== null) {
    if (body instanceof FormData || body instanceof Blob) {
      requestBody = body;
    } else {
      requestBody = JSON.stringify(body);
    }
  }

  const response = await fetch(url, {
    ...rest,
    body: requestBody,
    headers: customHeaders,
    credentials: "include",
  });

  if (!response.ok) {
    const { message, problems, raw } = await extractErrorMessage(response);
    throw new ApiError(response.status, message, problems, raw);
  }

  const disposition = response.headers.get("Content-Disposition");
  let filename: string | undefined;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename=["']?([^"';]+)["']?/);
    if (match) {
      filename = match[1];
    }
  }

  const blob = await response.blob();
  return { blob, filename };
}

export const api = {
  get: <T>(path: string, params?: RequestOptions["params"], options?: Omit<RequestOptions, "params">) =>
    apiFetch<T>(path, { method: "GET", params, ...options }),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { method: "POST", body, ...options }),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { method: "PUT", body, ...options }),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiFetch<T>(path, { method: "PATCH", body, ...options }),

  delete: <T>(path: string, options?: RequestOptions) =>
    apiFetch<T>(path, { method: "DELETE", ...options }),

  getBlob: (path: string, params?: RequestOptions["params"]) =>
    apiFetchBlob(path, { method: "GET", params }),
};
