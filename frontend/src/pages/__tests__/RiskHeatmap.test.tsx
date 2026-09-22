import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RiskHeatmap } from "../RiskHeatmap";
import { risksApi } from "../../api/risks";

vi.mock("../../api/risks", () => ({
  risksApi: {
    getHeatmap: vi.fn(),
  },
}));

const heatmap = (basis: "inherent" | "residual") => ({
  basis,
  matrix_size: 5,
  total_risks: 1,
  impact_labels: [
    { value: 1, label: "Insignificant" },
    { value: 2, label: "Minor" },
    { value: 3, label: "Moderate" },
    { value: 4, label: "Major" },
    { value: 5, label: "Severe" },
  ],
  likelihood_labels: [
    { value: 1, label: "Rare" },
    { value: 2, label: "Unlikely" },
    { value: 3, label: "Possible" },
    { value: 4, label: "Likely" },
    { value: 5, label: "Almost Certain" },
  ],
  rows: Array.from({ length: 5 }, (_, rowIndex) => ({
    likelihood: rowIndex + 1,
    likelihood_label: ["Rare", "Unlikely", "Possible", "Likely", "Almost Certain"][rowIndex],
    cells: Array.from({ length: 5 }, (_, columnIndex) => ({
      likelihood: rowIndex + 1,
      impact: columnIndex + 1,
      score: (rowIndex + 1) * (columnIndex + 1),
      band_name: "Medium",
      band_color: "#eab308",
      count: rowIndex === 2 && columnIndex === 2 ? 1 : 0,
      risks: rowIndex === 2 && columnIndex === 2
        ? [{ id: "risk-1", ref: "RISK-001", title: "Unauthorized access", inherent_score: 9, residual_score: 6, assurance_flag: "unsupported_residual" }]
        : [],
    })),
  })),
});

function renderHeatmap() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RiskHeatmap />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RiskHeatmap", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(risksApi.getHeatmap).mockImplementation(async (basis = "residual") => heatmap(basis));
  });

  it("renders the matrix and opens a cell's risk list", async () => {
    renderHeatmap();

    expect(await screen.findByRole("heading", { name: "5×5 Risk Heatmap" })).toBeInTheDocument();
    const cell = await screen.findByRole("button", { name: /Likelihood 3, Impact 3, score 9, Medium, 1 risk/ });
    expect(screen.getAllByRole("button", { name: /Likelihood \d, Impact \d, score/ })).toHaveLength(25);
    expect(screen.getByText("After controls")).toBeInTheDocument();
    fireEvent.click(cell);

    expect(screen.getByRole("dialog", { name: "Risks at likelihood 3, impact 3" })).toBeInTheDocument();
    expect(screen.getByText("RISK-001")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /RISK-001Unauthorized access/ })).toHaveAttribute("href", "/risks/risk-1");
  });

  it("switches between residual and inherent data", async () => {
    renderHeatmap();
    await screen.findByRole("button", { name: /Likelihood 3, Impact 3/ });
    fireEvent.click(screen.getByRole("button", { name: "Inherent" }));

    expect(await screen.findByText("Before controls")).toBeInTheDocument();
    expect(risksApi.getHeatmap).toHaveBeenLastCalledWith("inherent");
  });
});
