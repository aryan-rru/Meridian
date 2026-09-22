import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Download, FileSpreadsheet, Save, Upload, X } from "lucide-react";
import { importExportApi } from "../api/importexport";
import type { ImportSummary } from "../types";
import { useToast } from "../components/feedback/Toast";

function ImportSummaryPanel({ summary }: { summary: ImportSummary }) {
  return (
    <section className="import-summary" aria-labelledby="import-summary-heading">
      <div className="section-heading"><div><h3 id="import-summary-heading">Import summary</h3><p>Rows are upserted by their natural reference; invalid rows are reported without stopping the import.</p></div></div>
      <div className="import-summary-metrics"><div><strong>{summary.created}</strong><span>Created</span></div><div><strong>{summary.updated}</strong><span>Updated</span></div><div><strong>{summary.skipped}</strong><span>Skipped</span></div><div className={summary.errors.length ? "has-errors" : ""}><strong>{summary.errors.length}</strong><span>Errors</span></div></div>
      {summary.errors.length > 0 && <div className="import-errors"><h4><AlertCircle size={15} /> Row-level errors</h4>{summary.errors.map((error, index) => <div key={`${error.sheet}-${error.row}-${index}`}><b>{error.sheet}{error.row ? ` · row ${error.row}` : ""}</b><span>{error.message}</span></div>)}</div>}
      {Object.keys(summary.sheets).length > 0 && <div className="import-sheets">{Object.entries(summary.sheets).map(([sheet, counts]) => <div key={sheet}><strong>{sheet}</strong><span>{Object.entries(counts).map(([key, value]) => `${key}: ${value}`).join(" · ")}</span></div>)}</div>}
    </section>
  );
}

export function ImportExport() {
  const fileInput = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [summary, setSummary] = useState<ImportSummary | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [driveResult, setDriveResult] = useState<string | null>(null);
  const importMutation = useMutation({ mutationFn: importExportApi.importExcel, onSuccess: (data) => { setSummary(data); showToast(`Workbook imported: ${data.created} created, ${data.updated} updated.`); }, onError: (error: Error) => showToast(`Import failed. ${error.message}`, "error") });
  const driveMutation = useMutation({ mutationFn: importExportApi.exportToDrive, onSuccess: (data) => { setDriveResult(data.web_view_link || data.message); showToast("Export saved to Google Drive."); }, onError: (error: Error) => showToast(`Drive export failed. ${error.message}`, "error") });
  const chooseFile = (file?: File) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".xlsx")) { setSelectedFile(null); setDownloadError("Only .xlsx workbooks can be imported."); return; }
    setDownloadError(null); setSummary(null); setSelectedFile(file);
  };
  const download = async () => {
    setDownloadError(null);
    try {
      const response = await importExportApi.downloadExcel();
      const url = URL.createObjectURL(response.blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = response.filename || "meridian-export.xlsx";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "The export could not be downloaded.");
    }
  };

  return (
    <div className="page-container import-export-page">
      <div className="page-header"><div><h2>Import / Export</h2><p className="page-description">Move workspace data through a validated multi-sheet Excel workbook.</p></div></div>
      {downloadError && <div className="settings-alert error" role="alert"><AlertCircle size={17} />{downloadError}</div>}
      {importMutation.error && <div className="settings-alert error" role="alert"><AlertCircle size={17} />Import failed. {importMutation.error.message}</div>}
      {driveMutation.error && <div className="settings-alert error" role="alert"><AlertCircle size={17} />Drive export failed. {driveMutation.error.message}</div>}
      {driveResult && <div className="settings-alert success" role="status"><CheckCircle2 size={17} /> Export saved to Drive: {driveResult.startsWith("http") ? <a href={driveResult} target="_blank" rel="noreferrer">Open file</a> : driveResult}</div>}
      <div className="import-export-grid">
        <section className="import-export-card">
          <div className="import-export-card-icon"><Upload size={21} /></div>
          <h3>Import workspace data</h3>
          <p>Upload an .xlsx workbook to validate and upsert controls, requirements, risks, and mappings. Existing records are matched by reference.</p>
          <button type="button" className="secondary-btn" onClick={() => fileInput.current?.click()}><FileSpreadsheet size={16} /> Choose .xlsx file</button>
          <input ref={fileInput} hidden type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { chooseFile(event.target.files?.[0]); event.target.value = ""; }} />
          {selectedFile && <div className="selected-import-file"><FileSpreadsheet size={16} /><span>{selectedFile.name}<small>{(selectedFile.size / 1024).toFixed(1)} KB</small></span><button type="button" className="icon-btn" aria-label="Remove selected workbook" onClick={() => setSelectedFile(null)}><X size={15} /></button></div>}
          <button type="button" className="primary-btn import-submit" disabled={!selectedFile || importMutation.isPending} onClick={() => selectedFile && importMutation.mutate(selectedFile)}>{importMutation.isPending ? "Validating and importing..." : "Import workbook"}</button>
          <div className="workbook-sheets"><span>Expected sheets</span><b>Controls</b><b>Requirements</b><b>Crosswalk</b><b>Risks</b><b>RiskControls</b></div>
        </section>
        <section className="import-export-card">
          <div className="import-export-card-icon"><Download size={21} /></div>
          <h3>Export workspace data</h3>
          <p>Download a formatted multi-sheet workbook containing controls, requirements, mappings, risks, risk mappings, and evidence metadata.</p>
          <div className="import-export-actions"><button type="button" className="primary-btn" onClick={download}><Download size={16} /> Download Excel</button><button type="button" className="secondary-btn" disabled={driveMutation.isPending} onClick={() => driveMutation.mutate()}><Save size={16} /> {driveMutation.isPending ? "Saving..." : "Save to Drive"}</button></div>
          <div className="export-note">The Drive action creates a new export file and does not modify existing evidence files.</div>
        </section>
      </div>
      {summary && <ImportSummaryPanel summary={summary} />}
    </div>
  );
}
