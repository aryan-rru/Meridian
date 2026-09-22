import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProtectedRoute } from "../ProtectedRoute";
import { AuthProvider } from "../../../context/AuthContext";
import { authApi } from "../../../api/auth";

vi.mock("../../../api/auth", () => ({
  authApi: {
    getMe: vi.fn(),
    logout: vi.fn(),
    getGoogleLoginUrl: vi.fn(() => "http://localhost:8000/api/auth/google/login"),
  },
}));

describe("ProtectedRoute", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it("shows loading screen while session is being verified", () => {
    // Return a pending promise that never resolves during this check
    vi.mocked(authApi.getMe).mockReturnValue(new Promise(() => {}));

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <div>Protected Content</div>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/Loading meridian session/i)).toBeInTheDocument();
  });

  it("redirects unauthenticated users to /login", async () => {
    const error: any = new Error("Unauthorized");
    error.status = 401;
    vi.mocked(authApi.getMe).mockRejectedValue(error);

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/controls"]}>
            <Routes>
              <Route path="/login" element={<div>Login Page Target</div>} />
              <Route
                path="/controls"
                element={
                  <ProtectedRoute>
                    <div>Secret Controls</div>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    const loginTarget = await screen.findByText("Login Page Target");
    expect(loginTarget).toBeInTheDocument();
    expect(screen.queryByText("Secret Controls")).not.toBeInTheDocument();
  });

  it("renders protected content when user is authenticated", async () => {
    vi.mocked(authApi.getMe).mockResolvedValue({
      user: {
        id: "u-1",
        email: "alice@example.com",
        name: "Alice Security",
        picture_url: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      workspaces: [
        {
          workspace: {
            id: "ws-1",
            name: "Acme Corp GRC",
            evidence_folder_id: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
          role: "owner",
        },
      ],
      current_workspace: {
        id: "ws-1",
        name: "Acme Corp GRC",
        evidence_folder_id: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      current_role: "owner",
      google: {
        connected: true,
        configured: true,
        granted_scopes: ["drive.file"],
        can_browse_drive: false,
        can_read_sheets: false,
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={["/dashboard"]}>
            <Routes>
              <Route path="/login" element={<div>Login Page</div>} />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <div>Protected Dashboard Content</div>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    const content = await screen.findByText("Protected Dashboard Content");
    expect(content).toBeInTheDocument();
  });
});
