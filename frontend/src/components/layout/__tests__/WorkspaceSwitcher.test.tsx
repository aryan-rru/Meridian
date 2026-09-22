import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WorkspaceSwitcher } from "../WorkspaceSwitcher";
import { AuthProvider } from "../../../context/AuthContext";
import { authApi } from "../../../api/auth";
import { workspacesApi } from "../../../api/workspaces";

vi.mock("../../../api/auth", () => ({
  authApi: {
    getMe: vi.fn(),
    logout: vi.fn(),
  },
}));

vi.mock("../../../api/workspaces", () => ({
  workspacesApi: {
    list: vi.fn(),
    create: vi.fn(),
    switch: vi.fn(),
  },
}));

describe("WorkspaceSwitcher", () => {
  let queryClient: QueryClient;

  const mockSession = {
    user: {
      id: "u-1",
      email: "ciso@example.com",
      name: "Security Lead",
      picture_url: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    workspaces: [
      {
        workspace: {
          id: "ws-1",
          name: "Acme Production",
          evidence_folder_id: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
        role: "owner",
      },
      {
        workspace: {
          id: "ws-2",
          name: "Acme Staging",
          evidence_folder_id: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
        role: "member",
      },
    ],
    current_workspace: {
      id: "ws-1",
      name: "Acme Production",
      evidence_folder_id: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    current_role: "owner",
    google: {
      connected: true,
      configured: true,
      granted_scopes: [],
      can_browse_drive: false,
      can_read_sheets: false,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  it("displays current workspace name and user role in trigger button", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockSession);

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <WorkspaceSwitcher />
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText("Acme Production")).toBeInTheDocument();
    expect(screen.getByText("owner")).toBeInTheDocument();
  });

  it("opens dropdown and allows switching to another workspace", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockSession);
    vi.mocked(workspacesApi.switch).mockResolvedValue({
      current_workspace: mockSession.workspaces[1].workspace,
      role: "member",
      workspace_id: "ws-2",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <WorkspaceSwitcher />
        </AuthProvider>
      </QueryClientProvider>
    );

    // Wait until auth session has loaded
    expect(await screen.findByText("Acme Production")).toBeInTheDocument();

    const trigger = screen.getByRole("button", { name: /Switch workspace/i });
    fireEvent.click(trigger);

    // Both workspaces should be listed in the dropdown
    expect(screen.getByText("Your Workspaces")).toBeInTheDocument();
    expect(screen.getByText("Acme Staging")).toBeInTheDocument();

    const stagingOption = screen.getByText("Acme Staging").closest("button");
    expect(stagingOption).toBeInTheDocument();
    fireEvent.click(stagingOption!);

    await waitFor(() => {
      expect(workspacesApi.switch).toHaveBeenCalledWith("ws-2");
    });
  });

  it("allows creating a new workspace", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockSession);
    vi.mocked(workspacesApi.create).mockResolvedValue({
      id: "ws-3",
      name: "Acme Compliance Sandbox",
      evidence_folder_id: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    vi.mocked(workspacesApi.switch).mockResolvedValue({
      current_workspace: {
        id: "ws-3",
        name: "Acme Compliance Sandbox",
        evidence_folder_id: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      role: "owner",
      workspace_id: "ws-3",
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <WorkspaceSwitcher />
        </AuthProvider>
      </QueryClientProvider>
    );

    // Wait until auth session has loaded
    expect(await screen.findByText("Acme Production")).toBeInTheDocument();

    const trigger = screen.getByRole("button", { name: /Switch workspace/i });
    fireEvent.click(trigger);

    const createBtn = screen.getByRole("button", { name: /Create new workspace/i });
    fireEvent.click(createBtn);

    const input = screen.getByPlaceholderText(/Workspace name/i);
    fireEvent.change(input, { target: { value: "Acme Compliance Sandbox" } });

    const submitBtn = screen.getByRole("button", { name: /^Create$/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(workspacesApi.create).toHaveBeenCalledWith("Acme Compliance Sandbox");
      expect(workspacesApi.switch).toHaveBeenCalledWith("ws-3");
    });
  });
});
