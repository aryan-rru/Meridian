import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Dashboard } from "../Dashboard";
import { derivedApi } from "../../api/derived";

vi.mock("../../api/derived", () => ({
  derivedApi: {
    getDashboardSummary: vi.fn(),
  },
}));

const summary = {
  controls: {
    total: 10,
    by_status: { implemented: 6, partial: 2, not_implemented: 2, not_applicable: 0 },
    implemented_percent: 60,
  },
  coverage: {
    totals: { covered: 12, partial: 3, gap: 6, total_requirements: 21, coverage_percent: 57.1 },
    frameworks: [
      {
        framework_key: "iso27001",
        framework_name: "ISO 27001",
        color: "#2563eb",
        coverage_percent: 60,
        covered_count: 4,
        partial_count: 1,
        gap_count: 2,
        total_requirements: 7,
      },
    ],
  },
  gaps: {
    gap_count: 6,
    partial_count: 3,
    top_gaps: [
      { code: "A.5.1", framework_key: "iso27001", title: "Policies", status: "gap" },
    ],
  },
  risks: {
    total: 4,
    open: 3,
    unsupported_residual_count: 1,
    top_by_residual: [
      {
        id: "risk-1",
        ref: "RISK-001",
        title: "Unauthorized access",
        residual_score: 12,
        residual_band: { name: "High", color: "#f87171", index: 2 },
        assurance: { flag: "unsupported_residual" },
      },
    ],
    unsupported_residual: [{ id: "risk-1", ref: "RISK-001", title: "Unauthorized access" }],
  },
  remediation: {
    candidate_count: 2,
    top_items: [
      {
        control_id: "control-1",
        ref: "CTL-001",
        name: "Access reviews",
        category: "Access",
        status: "partial",
        priority_score: 8.5,
        risk_leverage: 1,
        weighted_risk_leverage: 1,
        requirement_leverage: 3,
        risks: [],
        requirements: [],
      },
    ],
  },
  evidence: { total: 5, by_status: { current: 3, stale: 1, missing: 1 } },
  leverage: { total_controls: 10, total_requirements: 21, total_mappings: 25, average_leverage: 2.5 },
};

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders summary cards, framework coverage, risks, remediation, and gaps", async () => {
    vi.mocked(derivedApi.getDashboardSummary).mockResolvedValue(summary);

    renderDashboard();

    expect(await screen.findByText("ISO 27001")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "60% of controls implemented" }),
    ).toBeInTheDocument();
    expect(screen.getByText("RISK-001")).toBeInTheDocument();
    expect(screen.getByText("CTL-001")).toBeInTheDocument();
    expect(screen.getByText("A.5.1")).toBeInTheDocument();
  });

  it("shows an actionable error when the summary request fails", async () => {
    vi.mocked(derivedApi.getDashboardSummary).mockRejectedValue(
      new Error("Workspace unavailable"),
    );

    renderDashboard();

    expect(await screen.findByRole("alert")).toHaveTextContent("Workspace unavailable");
  });
});
