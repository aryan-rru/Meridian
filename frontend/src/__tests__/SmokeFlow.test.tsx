import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { ToastProvider } from "../components/feedback/Toast";
import { authApi } from "../api/auth";
import { controlsApi } from "../api/controls";
import { frameworksApi } from "../api/frameworks";
import { derivedApi } from "../api/derived";

vi.mock("../api/auth", () => ({
  authApi: {
    getMe: vi.fn(),
    logout: vi.fn(),
    getGoogleLoginUrl: vi.fn(() => "/api/auth/google/login"),
  },
}));

vi.mock("../api/workspaces", () => ({
  workspacesApi: {
    list: vi.fn(),
    create: vi.fn(),
    switch: vi.fn(),
  },
}));

vi.mock("../api/controls", () => ({
  controlsApi: {
    list: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    get: vi.fn(),
    setRequirements: vi.fn(),
  },
}));

vi.mock("../api/frameworks", () => ({
  frameworksApi: {
    listRequirements: vi.fn(),
  },
}));

vi.mock("../api/derived", () => ({
  derivedApi: {
    getCrosswalk: vi.fn(),
  },
}));

const session = {
  user: { id: "user-1", email: "lead@example.com", name: "Security Lead", picture_url: null, created_at: "", updated_at: "" },
  workspaces: [{ workspace: { id: "workspace-1", name: "Main GRC", evidence_folder_id: null, created_at: "", updated_at: "" }, role: "owner" }],
  current_workspace: { id: "workspace-1", name: "Main GRC", evidence_folder_id: null, created_at: "", updated_at: "" },
  current_role: "owner",
  google: { connected: true, configured: true, granted_scopes: [], can_browse_drive: false, can_read_sheets: false },
};

const requirement = {
  id: "requirement-1",
  framework_id: "framework-1",
  framework_key: "iso27001",
  framework_name: "ISO 27001",
  framework_color: "#2563eb",
  code: "A.5.1",
  title: "Security policies",
  description: "",
  category: "Policies",
  sort_order: 1,
  mapped_control_count: 0,
  created_at: "",
  updated_at: "",
};

const control = {
  id: "control-1",
  workspace_id: "workspace-1",
  ref: "CTL-001",
  name: "Access reviews",
  description: "",
  category: "Access",
  owner: "Security",
  status: "partial" as const,
  implementation_notes: "",
  requirements_satisfied_count: 1,
  frameworks_touched: 1,
  framework_breakdown: { iso27001: 1 },
  risks_count: 0,
  evidence_count: 0,
  created_at: "",
  updated_at: "",
};

function renderApp(initialPath: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <MemoryRouter initialEntries={[initialPath]}>
            <AppRoutes />
          </MemoryRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe("frontend smoke flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authApi.getMe).mockResolvedValue(session);
    vi.mocked(frameworksApi.listRequirements).mockResolvedValue([requirement]);
    vi.mocked(controlsApi.list).mockResolvedValue([]);
    vi.mocked(controlsApi.create).mockResolvedValue(control);
    vi.mocked(controlsApi.setRequirements).mockResolvedValue({ ...control, requirements: [{ ...requirement, coverage_level: "full" }], risks: [], evidence: [] });
    vi.mocked(derivedApi.getCrosswalk).mockResolvedValue({
      column_groups: [{ framework_key: "iso27001", framework_name: "ISO 27001", framework_color: "#2563eb", columns: [{ requirement_id: requirement.id, code: requirement.code, title: requirement.title, category: requirement.category }] }],
      rows: [{ control_id: control.id, ref: control.ref, name: control.name, category: control.category, status: control.status, requirements_satisfied_count: 1, frameworks_touched: 1, framework_breakdown: { iso27001: 1 }, cells: { [requirement.id]: { coverage_level: "full" } } }],
      summary: { total_controls: 1, total_requirements: 1, total_mappings: 1, average_leverage: 1 },
    });
  });

  it("covers login access, control creation, mapping, and crosswalk visibility", async () => {
    const unauthorized = Object.assign(new Error("Unauthorized"), { status: 401 });
    vi.mocked(authApi.getMe).mockRejectedValueOnce(unauthorized);
    const loginRender = renderApp("/login");
    expect(await screen.findByRole("button", { name: /Sign in with Google/i })).toBeInTheDocument();
    loginRender.unmount();

    vi.mocked(authApi.getMe).mockResolvedValue(session);
    renderApp("/controls");
    expect(await screen.findByRole("heading", { name: "Control Library" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add control" }));
    fireEvent.change(screen.getByLabelText("Reference"), { target: { value: "CTL-001" } });
    fireEvent.change(screen.getByLabelText("Control name"), { target: { value: "Access reviews" } });
    fireEvent.click(screen.getByText("Security policies"));
    fireEvent.click(screen.getByRole("button", { name: "Create control" }));

    await waitFor(() => {
      expect(controlsApi.create).toHaveBeenCalledWith(expect.objectContaining({ ref: "CTL-001", name: "Access reviews" }));
      expect(controlsApi.setRequirements).toHaveBeenCalledWith("control-1", { items: [{ requirement_id: "requirement-1", coverage_level: "full" }] });
    });

    fireEvent.click(screen.getByRole("link", { name: "Crosswalk Matrix" }));
    expect(await screen.findByRole("heading", { name: "Crosswalk Matrix" })).toBeInTheDocument();
    expect(await screen.findByLabelText(/CTL-001 satisfies A\.5\.1/)).toBeInTheDocument();
  });
});
