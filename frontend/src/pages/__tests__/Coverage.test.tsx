import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Coverage } from "../Coverage";
import { derivedApi } from "../../api/derived";

vi.mock("../../api/derived", () => ({
  derivedApi: {
    getCoverage: vi.fn(),
    getGaps: vi.fn(),
  },
}));

const coverage = {
  frameworks: [
    {
      framework_key: "iso27001",
      framework_name: "ISO 27001",
      framework_color: "#2563eb",
      covered: 1,
      partial: 1,
      gap: 1,
      total: 3,
      coverage_percent: 33.3,
      categories: [
        { category: "Policies", covered: 1, partial: 1, gap: 1, total: 3, coverage_percent: 33.3 },
      ],
    },
  ],
  totals: { covered: 1, partial: 1, gap: 1, total_requirements: 3, coverage_percent: 33.3 },
};

const gaps = {
  gap_count: 1,
  partial_count: 1,
  items: [
    {
      requirement_id: "req-gap",
      framework_key: "iso27001",
      framework_name: "ISO 27001",
      code: "A.5.2",
      title: "Roles and responsibilities",
      category: "Policies",
      status: "gap" as const,
      mapped_controls: [],
      resolution_hint: "Create a control assigning security responsibilities.",
    },
    {
      requirement_id: "req-partial",
      framework_key: "iso27001",
      framework_name: "ISO 27001",
      code: "A.5.1",
      title: "Policies for information security",
      category: "Policies",
      status: "partial" as const,
      mapped_controls: [{ id: "control-1", ref: "CTL-001", name: "Access reviews", status: "partial", coverage_level: "partial" }],
      resolution_hint: "Strengthen the existing control.",
    },
  ],
};

function renderCoverage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Coverage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Coverage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(derivedApi.getCoverage).mockResolvedValue(coverage);
    vi.mocked(derivedApi.getGaps).mockResolvedValue(gaps);
  });

  it("renders framework/category heatmap and gap counts", async () => {
    renderCoverage();

    expect(await screen.findByText("ISO 27001")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Coverage Heatmap" })).toBeInTheDocument();
    expect(screen.getAllByText("33.3%").length).toBeGreaterThan(0);
    expect(screen.getByText("1 open gaps")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Policies gap: A.5.2/i })).toBeInTheDocument();
  });

  it("opens gap detail with resolution guidance and mapped controls", async () => {
    renderCoverage();
    await screen.findByRole("button", { name: /Policies gap: A.5.2/i });

    fireEvent.click(screen.getByRole("button", { name: /Policies gap: A.5.2/i }));

    expect(screen.getByRole("dialog", { name: "Gap detail for A.5.2" })).toBeInTheDocument();
    expect(screen.getByText("Create a control assigning security responsibilities.")).toBeInTheDocument();
  });
});
