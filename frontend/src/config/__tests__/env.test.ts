import { describe, it, expect } from "vitest";
import { config, buildApiUrl } from "../env";

describe("Environment Configuration", () => {
  it("provides apiBaseUrl without trailing slashes", () => {
    expect(config.apiBaseUrl).toBeDefined();
    expect(config.apiBaseUrl.endsWith("/")).toBe(false);
  });

  it("buildApiUrl handles leading slash properly", () => {
    const url = buildApiUrl("/controls");
    expect(url).toBe(`${config.apiBaseUrl}/controls`);
  });

  it("buildApiUrl handles missing leading slash properly", () => {
    const url = buildApiUrl("controls");
    expect(url).toBe(`${config.apiBaseUrl}/controls`);
  });
});
