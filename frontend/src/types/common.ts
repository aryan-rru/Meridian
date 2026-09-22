/**
 * Shared primitive and base types mirroring backend common schemas.
 */

export interface Timestamped {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface Band {
  name: string;
  color: string;
  index: number;
}

export interface Assurance {
  supporting_count: intCount;
  implemented_count: intCount;
  partial_count: intCount;
  not_implemented_count: intCount;
  not_applicable_count: intCount;
  weakest_status: string | null;
  claims_improvement: boolean;
  flag: "unsupported_residual" | null;
  message: string | null;
}

type intCount = number;

export interface ControlSummary {
  id: string;
  ref: string;
  name: string;
  status: string;
}

export interface Page<T> {
  items: T[];
  total: number;
}

export interface MessageResponse {
  message: string;
  detail?: Record<string, unknown> | null;
}

export interface ApiProblem {
  field: string;
  message: string;
}

export interface ApiErrorDetail {
  message: string;
  problems?: ApiProblem[];
}
