import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Crosswalk } from "../Crosswalk";
import { derivedApi } from "../../api/derived";

vi.mock("../../api/derived", () => ({
  derivedApi: {
    getCrosswalk: vi.fn(),
  },
}));

const crosswalk = {
  column_groups: [
    {
      framework_key: "iso27001",
      framework_name: "ISO 27001",
      framework_color: "#2563eb",
      columns: [
        {
          requirement_id: "req-1",
          code: "A.5.1",
          title: "Policies",
          category: "Policies",
        },
      ],
    },
    {
      framework_key: "soc2",
      framework_name: "SOC 2",
      framework_color: "#14b8a6",
      columns: [
        {
          requirement_id: "req-2",
          code: "CC1.1",
          title: "Control environment",
          category: "Governance",
        },
      ],
    },
  ],
  rows: [
    {
      control_id: "control-1",
      ref: "CTL-001",
      name: "Access reviews",
      category: "Access",
      status: "partial",
      requirements_satisfied_count: 1,
      frameworks_touched: 1,
      framework_breakdown: { iso27001: 1 },
      cells: {
        "req-1": { coverage_level: "full" as const },
        "req-2": null,
      },
    },
  ],
  summary: {
    total_controls: 1,
    total_requirements: 2,
    total_mappings: 1,
    average_leverage: 1,
  },
};

function renderCrosswalk() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Crosswalk />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Crosswalk", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(derivedApi.getCrosswalk).mockResolvedValue(crosswalk);
  });

  it("renders framework groups, mapped cells, empty cells, and leverage", async () => {
    renderCrosswalk();

    expect(await screen.findByText("ISO 27001")).toBeInTheDocument();
    expect(screen.getByText("SOC 2")).toBeInTheDocument();
    expect(screen.getByText("A.5.1")).toBeInTheDocument();
    expect(screen.getByText("CC1.1")).toBeInTheDocument();
    expect(screen.getByText("CTL-001")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /fw$/ })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /CTL-001 satisfies A.5.1/i })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /CTL-001 does not satisfy CC1.1/i })).toBeInTheDocument();
  });

  it("filters controls by search", async () => {
    renderCrosswalk();
    await screen.findByText("CTL-001");

    fireEvent.change(screen.getByRole("textbox", { name: "Search controls in crosswalk" }), {
      target: { value: "missing" },
    });

    expect(screen.getByText("No controls match your search.")).toBeInTheDocument();
  });
});
