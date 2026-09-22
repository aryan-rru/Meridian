import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RiskDetail } from "../RiskDetail";
import { risksApi } from "../../api/risks";

vi.mock("../../api/risks", () => ({
  risksApi: {
    getTraceability: vi.fn(),
  },
}));

const traceability = {
  risk: {
    id: "risk-1",
    ref: "RISK-001",
    title: "Unauthorized access",
    description: "Privileged access could be misused.",
    category: "Access",
    owner: "Security team",
    status: "open",
    treatment: "mitigate",
    inherent_score: 16,
    inherent_band: { name: "High", color: "#f87171" },
    residual_score: 6,
    residual_band: { name: "Medium", color: "#facc15" },
  },
  controls: [
    {
      control_id: "control-1",
      ref: "CTL-001",
      name: "Access reviews",
      status: "implemented",
      category: "Access",
      owner: "IT",
      evidence_count: 2,
      requirements_satisfied_count: 1,
      requirements: [
        {
          requirement_id: "req-1",
          code: "A.5.2",
          title: "Roles and responsibilities",
          category: "Policies",
          coverage_level: "full",
          framework: {
            framework_key: "iso27001",
            framework_name: "ISO 27001",
            color: "#2563eb",
          },
        },
      ],
    },
  ],
  assurance: {
    supporting_count: 1,
    implemented_count: 0,
    partial_count: 1,
    weakest_status: "partial",
    flag: "unsupported_residual",
    message: "Supporting controls are not implemented.",
  },
  aggregate: {
    control_count: 1,
    implemented_control_count: 0,
    distinct_requirement_count: 1,
    frameworks_touched: 1,
    frameworks: [
      {
        framework_key: "iso27001",
        framework_name: "ISO 27001",
        color: "#2563eb",
        requirement_count: 1,
      },
    ],
    weakest_control_status: "partial",
    total_evidence_count: 2,
  },
};

function renderRiskDetail() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/risks/risk-1"]}>
        <Routes>
          <Route path="/risks/:id" element={<RiskDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RiskDetail", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(risksApi.getTraceability).mockResolvedValue(traceability);
  });

  it("renders the risk summary, assurance warning, and full traceability tree", async () => {
    renderRiskDetail();

    expect(await screen.findByRole("heading", { name: "Risk Traceability: RISK-001" })).toBeInTheDocument();
    expect(screen.getByText("Unauthorized access")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Unearned residual risk" })).toBeInTheDocument();
    expect(screen.getByText("CTL-001 · Access reviews")).toBeInTheDocument();
    expect(screen.getByText("ISO 27001 · 1 requirements")).toBeInTheDocument();
    expect(screen.getByText("A.5.2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /2 linked evidence/i })).toHaveAttribute("href", "/evidence");
  });

  it("shows an API error without losing the page context", async () => {
    vi.mocked(risksApi.getTraceability).mockRejectedValue(new Error("Risk not found"));
    renderRiskDetail();

    expect(await screen.findByRole("alert")).toHaveTextContent("Risk traceability unavailable. Risk not found");
    expect(screen.getByRole("heading", { name: "Risk Traceability: risk-1" })).toBeInTheDocument();
  });
});
