import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppLayout } from "../AppLayout";
import { AuthProvider } from "../../../context/AuthContext";
import { authApi } from "../../../api/auth";

vi.mock("../../../api/auth", () => ({
  authApi: {
    getMe: vi.fn(),
    logout: vi.fn(),
    getGoogleLoginUrl: vi.fn(() => "http://localhost:8000/api/auth/google/login"),
  },
}));

vi.mock("../../../api/workspaces", () => ({
  workspacesApi: {
    list: vi.fn(),
    create: vi.fn(),
    switch: vi.fn(),
  },
}));

describe("AppLayout", () => {
  let queryClient: QueryClient;

  const mockUserSession = {
    user: {
      id: "u-1",
      email: "security-lead@acme.org",
      name: "Alex Vance",
      picture_url: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    workspaces: [
      {
        workspace: {
          id: "ws-alpha",
          name: "Acme Production GRC",
          evidence_folder_id: "f-123",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
        role: "admin",
      },
    ],
    current_workspace: {
      id: "ws-alpha",
      name: "Acme Production GRC",
      evidence_folder_id: "f-123",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    current_role: "admin",
    google: {
      connected: true,
      configured: true,
      granted_scopes: ["openid", "drive.file"],
      can_browse_drive: false,
      can_read_sheets: false,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it("renders the brand, navigation items, and current user info", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockUserSession);

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<div>Dashboard Child Page</div>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Brand and subtitle
    expect(await screen.findByText("meridian", { selector: ".brand-title" })).toBeInTheDocument();
    expect(screen.getByText("GRC Platform")).toBeInTheDocument();

    // Nav items
    expect(screen.getByRole("link", { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Control Library/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Crosswalk Matrix/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Coverage Heatmap/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Risk Register/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /5×5 Heatmap/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Remediation/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Evidence Library/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Import \/ Export/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Settings/i })).toBeInTheDocument();

    // User details and status
    expect(await screen.findByText("Alex Vance")).toBeInTheDocument();
    expect(screen.getByText("security-lead@acme.org")).toBeInTheDocument();
    expect(screen.getByText("Drive Linked")).toBeInTheDocument();

    // Header active workspace
    expect(screen.getByText("Acme Production GRC", { selector: ".tag-name" })).toBeInTheDocument();

    // Outlet child
    expect(screen.getByText("Dashboard Child Page")).toBeInTheDocument();
  });

  it("shows no-workspace alert banner when user has no active workspace", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue({
      ...mockUserSession,
      current_workspace: null,
      current_role: null,
      workspaces: [],
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<div>Dashboard Child Page</div>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    const banner = await screen.findByRole("alert");
    expect(banner).toBeInTheDocument();
    expect(screen.getByText(/No workspace selected/i)).toBeInTheDocument();
  });

  it("triggers logout when the logout button is clicked", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(mockUserSession);
    vi.mocked(authApi.logout).mockResolvedValue({ message: "Logged out successfully" });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route path="/" element={<AppLayout />} />
              <Route path="/login" element={<div>Redirected Login Page</div>} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    const logoutBtn = await screen.findByRole("button", { name: /Sign out/i });
    expect(logoutBtn).toBeInTheDocument();

    fireEvent.click(logoutBtn);
    await waitFor(() => expect(authApi.logout).toHaveBeenCalledTimes(1));
  });
});
