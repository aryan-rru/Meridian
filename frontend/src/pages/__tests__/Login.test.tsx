import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Login } from "../Login";
import { AuthProvider } from "../../context/AuthContext";
import { authApi } from "../../api/auth";

vi.mock("../../api/auth", () => ({
  authApi: {
    getMe: vi.fn(),
    getGoogleLoginUrl: vi.fn(() => "/api/auth/google/login"),
    logout: vi.fn(),
  },
}));

function renderLogin(initialEntry = "/login") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Login />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts Google sign-in from the configured API URL", async () => {
    const unauthorized = Object.assign(new Error("Unauthorized"), { status: 401 });
    vi.mocked(authApi.getMe).mockRejectedValue(unauthorized);
    vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      href: "",
    } as Location);

    renderLogin();
    const button = await screen.findByRole("button", { name: /Sign in with Google/i });
    fireEvent.click(button);

    expect(authApi.getGoogleLoginUrl).toHaveBeenCalledTimes(1);
  });

  it("explains when Google access is cancelled", async () => {
    const unauthorized = Object.assign(new Error("Unauthorized"), { status: 401 });
    vi.mocked(authApi.getMe).mockRejectedValue(unauthorized);

    renderLogin("/login?error=access_denied");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Google sign-in was cancelled",
    );
  });

  it("reports session verification failures", async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(new Error("Network unavailable"));

    renderLogin();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We could not verify your session",
    );
  });
});
