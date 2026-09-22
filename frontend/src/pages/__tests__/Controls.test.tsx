import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Controls } from "../Controls";
import { controlsApi } from "../../api/controls";
import { frameworksApi } from "../../api/frameworks";

vi.mock("../../api/controls", () => ({
  controlsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    get: vi.fn(),
    setRequirements: vi.fn(),
  },
}));

vi.mock("../../api/frameworks", () => ({
  frameworksApi: {
    listRequirements: vi.fn(),
  },
}));

const control = {
  id: "control-1",
  workspace_id: "workspace-1",
  ref: "CTL-001",
  name: "Access reviews",
  description: "Review access quarterly.",
  category: "Access",
  owner: "Security",
  status: "partial" as const,
  implementation_notes: "",
  requirements_satisfied_count: 1,
  frameworks_touched: 1,
  framework_breakdown: { iso27001: 1 },
  risks_count: 0,
  evidence_count: 0,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const requirement = {
  id: "requirement-1",
  framework_id: "framework-1",
  framework_key: "iso27001",
  framework_name: "ISO 27001",
  framework_color: "#2563eb",
  code: "A.5.1",
  title: "Policies for information security",
  description: "",
  category: "Policies",
  sort_order: 1,
  mapped_control_count: 1,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderControls() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Controls />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Controls", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(controlsApi.list).mockResolvedValue([control]);
    vi.mocked(frameworksApi.listRequirements).mockResolvedValue([requirement]);
    vi.mocked(controlsApi.create).mockResolvedValue(control);
    vi.mocked(controlsApi.setRequirements).mockResolvedValue({
      ...control,
      requirements: [{ ...requirement, coverage_level: "full" }],
      risks: [],
      evidence: [],
    });
  });

  it("renders computed leverage counts and filters the control list", async () => {
    renderControls();

    expect(await screen.findByText("CTL-001")).toBeInTheDocument();
    expect(screen.getAllByText("1")).toHaveLength(2);
    expect(screen.getByText("answered")).toBeInTheDocument();
    expect(screen.getByText("frameworks")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("textbox", { name: "Search controls" }), {
      target: { value: "does-not-match" },
    });

    await waitFor(() => {
      expect(controlsApi.list).toHaveBeenLastCalledWith({
        q: "does-not-match",
        status: "",
        category: "",
      });
    });
  });

  it("creates a control and submits its requirement mappings", async () => {
    renderControls();
    await screen.findByText("CTL-001");

    fireEvent.click(screen.getByRole("button", { name: "Add control" }));
    fireEvent.change(screen.getByLabelText("Reference"), { target: { value: "CTL-002" } });
    fireEvent.change(screen.getByLabelText("Control name"), { target: { value: "Joiner process" } });
    fireEvent.click(screen.getByText("Policies for information security"));
    fireEvent.click(screen.getByRole("button", { name: "Create control" }));

    await waitFor(() => {
      expect(controlsApi.create).toHaveBeenCalledWith(expect.objectContaining({
        ref: "CTL-002",
        name: "Joiner process",
      }));
      expect(controlsApi.setRequirements).toHaveBeenCalledWith("control-1", {
        items: [{ requirement_id: "requirement-1", coverage_level: "full" }],
      });
    });
  });
});
