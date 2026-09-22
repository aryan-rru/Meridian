import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Risks } from "../Risks";
import { risksApi } from "../../api/risks";
import { settingsApi } from "../../api/settings";

vi.mock("../../api/risks", () => ({
  risksApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../../api/settings", () => ({
  settingsApi: {
    getSettings: vi.fn(),
  },
}));

const risk = {
  id: "risk-1",
  ref: "RISK-001",
  title: "Unauthorized access",
  description: "Excess privilege may expose systems.",
  category: "Access",
  owner: "Security",
  treatment: "mitigate" as const,
  status: "open" as const,
  inherent_likelihood: 4,
  inherent_impact: 4,
  residual_likelihood: 2,
  residual_impact: 3,
  inherent_likelihood_label: "Likely",
  inherent_impact_label: "Major",
  residual_likelihood_label: "Unlikely",
  residual_impact_label: "Moderate",
  inherent_score: 16,
  inherent_band: { name: "High", color: "#f87171", index: 2 },
  residual_score: 6,
  residual_band: { name: "Medium", color: "#facc15", index: 1 },
  score_reduction: 10,
  assurance: {
    supporting_count: 1,
    implemented_count: 0,
    partial_count: 1,
    not_implemented_count: 0,
    not_applicable_count: 0,
    weakest_status: "partial",
    claims_improvement: true,
    flag: "unsupported_residual" as const,
    message: "Supporting controls are not implemented.",
  },
  controls: [],
  control_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const settings = {
  matrix_size: 5,
  score_method: "multiply" as const,
  weights: { wL: 0.5, wI: 0.5 },
  likelihood_labels: { "1": "Rare", "2": "Unlikely", "3": "Possible", "4": "Likely", "5": "Almost certain" },
  impact_labels: { "1": "Minimal", "2": "Minor", "3": "Moderate", "4": "Major", "5": "Severe" },
  risk_bands: [{ name: "High", min: 10, max: 25, color: "#f87171" }],
  remediation_weights: { W_RISK: 1, W_REQ: 0.5 },
  evidence_stale_after_days: 90,
  min_possible_score: 1,
  max_possible_score: 25,
};

function renderRisks() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Risks />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Risks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(risksApi.list).mockResolvedValue([risk]);
    vi.mocked(settingsApi.getSettings).mockResolvedValue(settings);
    vi.mocked(risksApi.create).mockResolvedValue(risk);
  });

  it("renders inherent/residual bands and unearned residual warning", async () => {
    renderRisks();

    expect(await screen.findByText("RISK-001")).toBeInTheDocument();
    expect(screen.getAllByText("High").length).toBeGreaterThan(0);
    expect(screen.getByText("Medium")).toBeInTheDocument();
    expect(screen.getByText("Unearned residual")).toBeInTheDocument();
  });

  it("uses configured plain-English labels in the risk form", async () => {
    renderRisks();
    await screen.findByText("RISK-001");
    fireEvent.click(screen.getByRole("button", { name: "Add risk" }));

    expect(screen.getAllByRole("option", { name: "3 — Possible" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("option", { name: "4 — Major" }).length).toBeGreaterThan(0);
  });

  it("creates a risk with configured score inputs", async () => {
    renderRisks();
    await screen.findByText("RISK-001");
    fireEvent.click(screen.getByRole("button", { name: "Add risk" }));
    fireEvent.change(screen.getByLabelText("Reference"), { target: { value: "RISK-002" } });
    fireEvent.change(screen.getByLabelText("Risk title"), { target: { value: "Data loss" } });
    fireEvent.click(screen.getByRole("button", { name: "Create risk" }));

    await waitFor(() => {
      expect(risksApi.create).toHaveBeenCalledWith(expect.objectContaining({
        ref: "RISK-002",
        title: "Data loss",
      }));
    });
  });
});
