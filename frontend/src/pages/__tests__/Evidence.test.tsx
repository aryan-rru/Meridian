import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Evidence } from "../Evidence";
import { evidenceApi } from "../../api/evidence";
import { controlsApi } from "../../api/controls";

vi.mock("../../api/evidence", () => ({
  evidenceApi: {
    listEvidence: vi.fn(),
    listDriveFiles: vi.fn(),
    linkEvidence: vi.fn(),
    uploadEvidence: vi.fn(),
    extractEvidence: vi.fn(),
  },
}));

vi.mock("../../api/controls", () => ({
  controlsApi: {
    list: vi.fn(),
  },
}));

const controls = [{
  id: "control-1",
  workspace_id: "workspace-1",
  ref: "CTL-001",
  name: "Access reviews",
  description: "",
  category: "Access",
  owner: "IT",
  status: "partial" as const,
  implementation_notes: "",
  requirements_satisfied_count: 1,
  frameworks_touched: 1,
  framework_breakdown: { iso27001: 1 },
  risks_count: 1,
  evidence_count: 1,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
}];
const evidence = [{
  id: "evidence-1",
  workspace_id: "workspace-1",
  control_id: "control-1",
  control_ref: "CTL-001",
  control_name: "Access reviews",
  title: "Access review workbook",
  description: "",
  source_type: "google_sheet" as const,
  drive_file_name: "access-reviews.xlsx",
  mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  web_view_link: "https://drive.google.com/file/evidence-1",
  status: "stale" as const,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
}];

function renderEvidence() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Evidence />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Evidence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(controlsApi.list).mockResolvedValue(controls);
    vi.mocked(evidenceApi.listEvidence).mockResolvedValue(evidence);
    vi.mocked(evidenceApi.listDriveFiles).mockResolvedValue({ files: [{ id: "drive-1", name: "policy.xlsx", mimeType: "application/vnd.google-apps.spreadsheet", webViewLink: null }], scope_limited: false });
    vi.mocked(evidenceApi.linkEvidence).mockResolvedValue(evidence[0]);
    vi.mocked(evidenceApi.extractEvidence).mockResolvedValue({ evidence_id: "evidence-1", status: "current", message: "Extracted" });
  });

  it("renders freshness status and extracts spreadsheet evidence", async () => {
    renderEvidence();

    expect(await screen.findByText("Access review workbook")).toBeInTheDocument();
    expect(screen.getAllByText("Stale").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Extract values" }));

    await waitFor(() => expect(evidenceApi.extractEvidence).toHaveBeenCalledWith("evidence-1"));
  });

  it("opens Drive search and links a selected file to a control", async () => {
    renderEvidence();
    await screen.findByText("Access review workbook");
    fireEvent.click(screen.getByRole("button", { name: /CTL-001/ }));

    expect(await screen.findByRole("dialog", { name: "Choose evidence from Drive" })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: /policy\.xlsx/ }));
    fireEvent.click(screen.getByRole("button", { name: "Link selected file" }));

    await waitFor(() => expect(evidenceApi.linkEvidence).toHaveBeenCalledWith(expect.objectContaining({
      control_id: "control-1",
      drive_file_id: "drive-1",
    })));
  });
});
