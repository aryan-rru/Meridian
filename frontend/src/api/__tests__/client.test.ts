import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { api, ApiError } from "../client";
import { authApi } from "../auth";
import { controlsApi } from "../controls";
import { risksApi } from "../risks";

describe("API Client", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("sends credentials: 'include' with every request", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ status: "ok" }),
    });
    globalThis.fetch = fetchMock;

    await api.get("/health");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/health");
    expect(init.credentials).toBe("include");
  });

  it("sets Content-Type: application/json for JSON payloads", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ id: "123", ref: "CTL-001" }),
    });
    globalThis.fetch = fetchMock;

    await api.post("/controls", { ref: "CTL-001", name: "MFA" });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.get("Content-Type")).toBe("application/json");
    expect(init.body).toBe(JSON.stringify({ ref: "CTL-001", name: "MFA" }));
  });

  it("does not force application/json when body is FormData", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ created: 10 }),
    });
    globalThis.fetch = fetchMock;

    const formData = new FormData();
    formData.append("file", new Blob(["dummy"]), "test.xlsx");

    await api.post("/import/excel", formData);

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers.get("Content-Type")).toBeNull();
    expect(init.body).toBe(formData);
  });

  it("correctly appends query parameters, omitting null/undefined/empty", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => [],
    });
    globalThis.fetch = fetchMock;

    await api.get("/controls", { status: "implemented", category: undefined, q: "MFA" });

    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/controls?status=implemented&q=MFA");
  });

  it("throws structured ApiError on 422 validation failure with problem fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({
        detail: {
          message: "Some fields need attention before this can be saved.",
          problems: [{ field: "name", message: "Field required" }],
        },
      }),
    });
    globalThis.fetch = fetchMock;

    await expect(api.post("/controls", {})).rejects.toThrow(ApiError);

    try {
      await api.post("/controls", {});
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(422);
      expect(apiErr.message).toBe("Some fields need attention before this can be saved.");
      expect(apiErr.problems).toEqual([{ field: "name", message: "Field required" }]);
    }
  });

  it("handles 401 unauthenticated errors cleanly", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ detail: "Authentication required." }),
    });
    globalThis.fetch = fetchMock;

    try {
      await authApi.getMe();
      expect.fail("Should have thrown");
    } catch (err) {
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(401);
      expect(apiErr.message).toBe("Authentication required.");
    }
  });

  it("returns undefined on 204 No Content", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      headers: new Headers(),
    });
    globalThis.fetch = fetchMock;

    const result = await api.delete("/controls/123");
    expect(result).toBeUndefined();
  });

  it("calls controlsApi.setRequirements with PUT and correct payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ id: "ctl-1" }),
    });
    globalThis.fetch = fetchMock;

    await controlsApi.setRequirements("ctl-1", {
      items: [{ requirement_id: "req-1", coverage_level: "full" }],
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/controls/ctl-1/requirements");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({
      items: [{ requirement_id: "req-1", coverage_level: "full" }],
    });
  });

  it("calls risksApi.setControls with PUT and correct payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      json: async () => ({ id: "risk-1" }),
    });
    globalThis.fetch = fetchMock;

    await risksApi.setControls("risk-1", ["ctl-1", "ctl-2"]);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/risks/risk-1/controls");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual({
      control_ids: ["ctl-1", "ctl-2"],
    });
  });
});
