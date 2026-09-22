import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Settings } from "../Settings";
import { settingsApi } from "../../api/settings";

vi.mock("../../api/settings", () => ({
  settingsApi: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

const settings = {
  matrix_size: 5,
  score_method: "multiply" as const,
  weights: { wL: 1, wI: 1 },
  likelihood_labels: { "1": "Rare", "2": "Unlikely", "3": "Possible", "4": "Likely", "5": "Almost Certain" },
  impact_labels: { "1": "Insignificant", "2": "Minor", "3": "Moderate", "4": "Major", "5": "Severe" },
  risk_bands: [
    { name: "Low", min: 1, max: 4, color: "#16a34a" },
    { name: "Medium", min: 5, max: 9, color: "#eab308" },
    { name: "High", min: 10, max: 15, color: "#f97316" },
    { name: "Critical", min: 16, max: 25, color: "#dc2626" },
  ],
  remediation_weights: { W_RISK: 1, W_REQ: 0.5 },
  evidence_stale_after_days: 365,
  min_possible_score: 1,
  max_possible_score: 25,
};

function renderSettings() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}><Settings /></QueryClientProvider>);
}

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(settingsApi.getSettings).mockResolvedValue(settings);
    vi.mocked(settingsApi.updateSettings).mockResolvedValue(settings);
  });

  it("renders configurable labels, scoring, bands, and remediation weights", async () => {
    renderSettings();

    expect(await screen.findByLabelText("Likelihood 3 label")).toHaveValue("Possible");
    expect(screen.getByLabelText("Impact 5 label")).toHaveValue("Severe");
    expect(screen.getByLabelText("Band 4 name")).toHaveValue("Critical");
    expect(screen.getByRole("combobox", { name: "Score method" })).toHaveValue("multiply");
    expect(screen.getByRole("combobox", { name: "Matrix size" })).toHaveValue("5");
  });

  it("validates band coverage before saving and submits updated labels", async () => {
    renderSettings();
    await screen.findByLabelText("Likelihood 3 label");
    fireEvent.change(screen.getByLabelText("Band 1 minimum"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Risk bands must cover the full score range");
    expect(settingsApi.updateSettings).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Band 1 minimum"), { target: { value: "1" } });
    fireEvent.change(screen.getByLabelText("Likelihood 3 label"), { target: { value: "Possible for us" } });
    fireEvent.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(settingsApi.updateSettings).toHaveBeenCalledWith(expect.objectContaining({
      likelihood_labels: expect.objectContaining({ "3": "Possible for us" }),
    })));
  });
});
