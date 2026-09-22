import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ImportExport } from "../ImportExport";
import { importExportApi } from "../../api/importexport";

vi.mock("../../api/importexport", () => ({
  importExportApi: {
    importExcel: vi.fn(),
    downloadExcel: vi.fn(),
    exportToDrive: vi.fn(),
  },
}));

const summary = {
  created: 3,
  updated: 2,
  skipped: 1,
  errors: [{ sheet: "Controls", row: 4, message: "Status is invalid." }],
  sheets: { Controls: { created: 3, updated: 2 }, Risks: { skipped: 1 } },
};

function renderImportExport() {
  const queryClient = new QueryClient();
  return render(<QueryClientProvider client={queryClient}><ImportExport /></QueryClientProvider>);
}

describe("ImportExport", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(importExportApi.importExcel).mockResolvedValue(summary);
    vi.mocked(importExportApi.exportToDrive).mockResolvedValue({ file_id: "file-1", name: "meridian-export.xlsx", web_view_link: "https://drive.google.com/export", message: "Saved" });
    vi.mocked(importExportApi.downloadExcel).mockResolvedValue({ blob: new Blob(["xlsx"]), filename: "workspace.xlsx" });
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:export"), revokeObjectURL: vi.fn() });
  });

  it("imports an xlsx workbook and renders the validation summary", async () => {
    renderImportExport();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["workbook"], "workspace.xlsx", { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Import workbook" }));

    expect(await screen.findByRole("heading", { name: "Import summary" })).toBeInTheDocument();
    expect(screen.getByText("Status is invalid.")).toBeInTheDocument();
    expect(importExportApi.importExcel).toHaveBeenCalledWith(file, expect.anything());
  });

  it("downloads an export and saves a copy to Drive", async () => {
    renderImportExport();
    fireEvent.click(screen.getByRole("button", { name: "Download Excel" }));
    await waitFor(() => expect(importExportApi.downloadExcel).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Save to Drive" }));
    await waitFor(() => expect(importExportApi.exportToDrive).toHaveBeenCalled());
    expect(await screen.findByRole("link", { name: "Open file" })).toHaveAttribute("href", "https://drive.google.com/export");
  });
});
