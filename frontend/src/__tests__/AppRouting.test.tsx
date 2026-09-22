import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppRoutes } from "../App";
import { AuthProvider } from "../context/AuthContext";
import { authApi } from "../api/auth";

vi.mock("../api/auth", () => ({
  authApi: {
    getMe: vi.fn(),
    logout: vi.fn(),
    getGoogleLoginUrl: vi.fn(() => "http://localhost:8000/api/auth/google/login"),
  },
}));

vi.mock("../api/workspaces", () => ({
  workspacesApi: {
    list: vi.fn(),
    create: vi.fn(),
    switch: vi.fn(),
  },
}));

describe("Application Routing", () => {
  let queryClient: QueryClient;

  const authenticatedSession = {
    user: {
      id: "u-1",
      email: "user@example.com",
      name: "Security Lead",
      picture_url: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    workspaces: [
      {
        workspace: {
          id: "ws-1",
          name: "Main GRC",
          evidence_folder_id: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
        role: "owner",
      },
    ],
    current_workspace: {
      id: "ws-1",
      name: "Main GRC",
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

  const renderRoute = (initialPath: string) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={[initialPath]}>
            <AppRoutes />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );
  };

  it("renders the login page when accessing /login directly", async () => {
    const error: any = new Error("Unauthorized");
    error.status = 401;
    vi.mocked(authApi.getMe).mockRejectedValue(error);

    renderRoute("/login");
    expect(await screen.findByRole("heading", { name: /Sign in to meridian/i })).toBeInTheDocument();
  });

  it("redirects unauthenticated user to /login from protected routes", async () => {
    const error: any = new Error("Unauthorized");
    error.status = 401;
    vi.mocked(authApi.getMe).mockRejectedValue(error);

    renderRoute("/crosswalk");
    expect(await screen.findByRole("heading", { name: /Sign in to meridian/i })).toBeInTheDocument();
  });

  it("renders the Dashboard on root / route when authenticated", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/");
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  });

  it("renders Control Library on /controls route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/controls");
    expect(await screen.findByRole("heading", { name: "Control Library" })).toBeInTheDocument();
  });

  it("renders Crosswalk Matrix on /crosswalk route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/crosswalk");
    expect(await screen.findByRole("heading", { name: "Crosswalk Matrix" })).toBeInTheDocument();
  });

  it("renders Coverage Heatmap on /coverage route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/coverage");
    expect(await screen.findByRole("heading", { name: "Coverage Heatmap" })).toBeInTheDocument();
  });

  it("renders Risk Register on /risks route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/risks");
    expect(await screen.findByRole("heading", { name: "Risk Register" })).toBeInTheDocument();
  });

  it("renders Risk Detail on /risks/:id route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/risks/RSK-042");
    expect(await screen.findByRole("heading", { name: "Risk Traceability: RSK-042" })).toBeInTheDocument();
  });

  it("renders 5×5 Risk Heatmap on /risk-heatmap route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/risk-heatmap");
    expect(await screen.findByRole("heading", { name: "5×5 Risk Heatmap" })).toBeInTheDocument();
  });

  it("renders Remediation on /remediation route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/remediation");
    expect(await screen.findByRole("heading", { name: "Remediation Priority" })).toBeInTheDocument();
  });

  it("renders Evidence Library on /evidence route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/evidence");
    expect(await screen.findByRole("heading", { name: "Evidence Library" })).toBeInTheDocument();
  });

  it("renders Settings on /settings route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/settings");
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument();
  });

  it("renders Import/Export on /import-export route", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue(authenticatedSession);

    renderRoute("/import-export");
    expect(await screen.findByRole("heading", { name: "Import / Export" })).toBeInTheDocument();
  });

  it("renders NotFound 404 page on unrecognized routes", async () => {
    renderRoute("/this-route-does-not-exist-at-all");
    expect(await screen.findByRole("heading", { name: "Page Not Found" })).toBeInTheDocument();
  });
});
