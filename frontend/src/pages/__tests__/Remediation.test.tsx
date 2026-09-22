import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Remediation } from "../Remediation";
import { derivedApi } from "../../api/derived";

vi.mock("../../api/derived", () => ({
  derivedApi: {
    getRemediation: vi.fn(),
  },
}));

const remediation = {
  items: [
    {
      control_id: "control-1",
      ref: "CTL-001",
      name: "Access reviews",
      category: "Access",
      status: "partial",
      priority_score: 18.5,
      risk_leverage: 2,
      weighted_risk_leverage: 17.5,
      requirement_leverage: 2,
      risks: [
        { id: "risk-1", ref: "RISK-001", title: "Unauthorized access", inherent_score: 10 },
      ],
      requirements: [
        { id: "req-1", framework_key: "iso27001", code: "A.5.2", title: "Roles and responsibilities" },
      ],
    },
    {
      control_id: "control-2",
      ref: "CTL-002",
      name: "Asset inventory",
      category: "Assets",
      status: "not_implemented",
      priority_score: 4,
      risk_leverage: 0,
      weighted_risk_leverage: 0,
      requirement_leverage: 2,
      risks: [],
      requirements: [],
    },
  ],
  weights: { W_RISK: 1, W_REQ: 0.5 },
  candidate_count: 2,
};

function renderRemediation() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Remediation />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Remediation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(derivedApi.getRemediation).mockResolvedValue(remediation);
  });

  it("renders ranked controls with leverage, risks, and requirements", async () => {
    renderRemediation();

    expect(await screen.findByText("Fix the control propping up the most risk first.")).toBeInTheDocument();
    expect(screen.getByText("CTL-001")).toBeInTheDocument();
    expect(screen.getByText("18.5")).toBeInTheDocument();
    expect(screen.getByText("RISK-001")).toBeInTheDocument();
    expect(screen.getByText("A.5.2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /RISK-001/ })).toHaveAttribute("href", "/risks/risk-1");
  });

  it("filters remediation items across control and risk text", async () => {
    renderRemediation();
    await screen.findByText("CTL-001");
    fireEvent.change(screen.getByLabelText("Search remediation items"), { target: { value: "asset inventory" } });

    expect(screen.getByText("CTL-002")).toBeInTheDocument();
    expect(screen.queryByText("CTL-001")).not.toBeInTheDocument();
  });
});
