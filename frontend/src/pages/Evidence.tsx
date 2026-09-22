import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, ExternalLink, FileSpreadsheet, FileText, Link2, Search, Upload, X } from "lucide-react";
import { controlsApi } from "../api/controls";
import { evidenceApi } from "../api/evidence";
import type { Control, DriveFile, Evidence, EvidenceStatus } from "../types";

function statusLabel(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function EvidenceIcon({ mimeType }: { mimeType: string }) {
  return mimeType.includes("spreadsheet") || mimeType.includes("excel") ? <FileSpreadsheet size={19} /> : <FileText size={19} />;
}

function EvidenceCard({ evidence, onExtract, extracting }: { evidence: Evidence; onExtract: (id: string) => void; extracting: boolean }) {
  return (
    <article className="evidence-card">
      <div className="evidence-card-icon"><EvidenceIcon mimeType={evidence.mime_type} /></div>
      <div className="evidence-card-main">
        <div className="evidence-card-header">
          <div>
            <h3>{evidence.title || evidence.drive_file_name}</h3>
            <p>{evidence.drive_file_name} · {evidence.control_ref || evidence.control_name || "Unassigned control"}</p>
          </div>
          <span className={`evidence-status ${evidence.status}`}><i />{statusLabel(evidence.status)}</span>
        </div>
        <div className="evidence-card-meta">
          <span>{statusLabel(evidence.source_type)}</span>
          {evidence.valid_until && <span>Valid until {new Date(evidence.valid_until).toLocaleDateString()}</span>}
          {evidence.extracted_at && <span>Extracted {new Date(evidence.extracted_at).toLocaleDateString()}</span>}
        </div>
        <div className="evidence-card-actions">
          {evidence.web_view_link && <a href={evidence.web_view_link} target="_blank" rel="noreferrer"><ExternalLink size={14} /> Open in Drive</a>}
          {(evidence.source_type === "google_sheet" || evidence.mime_type.includes("spreadsheet") || evidence.mime_type.includes("excel")) && (
            <button type="button" onClick={() => onExtract(evidence.id)} disabled={extracting}>{extracting ? "Extracting..." : "Extract values"}</button>
          )}
        </div>
      </div>
    </article>
  );
}

function DrivePicker({ controlId, onClose, onLinked }: { controlId: string; onClose: () => void; onLinked: () => void }) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<DriveFile | null>(null);
  const [title, setTitle] = useState("");
  const [validUntil, setValidUntil] = useState("");
  const filesQuery = useQuery({
    queryKey: ["drive-files", search],
    queryFn: () => evidenceApi.listDriveFiles({ q: search || undefined, page_size: 25 }),
    retry: false,
  });
  const linkMutation = useMutation({
    mutationFn: () => evidenceApi.linkEvidence({
      control_id: controlId,
      drive_file_id: selected?.id,
      title: title || selected?.name,
      valid_until: validUntil || undefined,
      source_type: selected?.mimeType.includes("spreadsheet") ? "google_sheet" : "drive_file",
    }),
    onSuccess: onLinked,
  });

  return (
    <div className="modal-backdrop">
      <section className="evidence-picker-modal" role="dialog" aria-modal="true" aria-labelledby="drive-picker-heading">
        <div className="modal-header"><div><h3 id="drive-picker-heading">Choose evidence from Drive</h3><p>Search files you have explicitly shared with Meridian.</p></div><button type="button" className="icon-btn" onClick={onClose} aria-label="Close Drive picker"><X size={18} /></button></div>
        <label className="picker-search"><Search size={15} /><input aria-label="Search Drive files" placeholder="Search Drive files..." value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <div className="drive-file-list">
          {filesQuery.isLoading && <p className="detail-muted">Searching Drive...</p>}
          {filesQuery.error && <p className="form-error">Drive search unavailable. {filesQuery.error.message}</p>}
          {(filesQuery.data?.files ?? []).map((file) => (
            <button type="button" className={`drive-file-option ${selected?.id === file.id ? "selected" : ""}`} key={file.id} onClick={() => { setSelected(file); setTitle(file.name); }}>
              <EvidenceIcon mimeType={file.mimeType} /><span><strong>{file.name}</strong><small>{file.mimeType}</small></span><CheckCircle2 size={16} />
            </button>
          ))}
          {!filesQuery.isLoading && !filesQuery.error && (filesQuery.data?.files ?? []).length === 0 && <p className="detail-muted">No Drive files found.</p>}
        </div>
        {selected && <div className="evidence-picker-fields"><label>Evidence title<input value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Valid until<input type="date" value={validUntil} onChange={(event) => setValidUntil(event.target.value)} /></label></div>}
        <div className="modal-actions"><button type="button" className="secondary-btn" onClick={onClose}>Cancel</button><button type="button" className="primary-btn" disabled={!selected || linkMutation.isPending} onClick={() => linkMutation.mutate()}>{linkMutation.isPending ? "Linking..." : "Link selected file"}</button></div>
        {linkMutation.error && <p className="form-error">{linkMutation.error.message}</p>}
      </section>
    </div>
  );
}

export function Evidence() {
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [controlFilter, setControlFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<EvidenceStatus | "">("");
  const [pickerControl, setPickerControl] = useState<string | null>(null);
  const [uploadControl, setUploadControl] = useState("");
  const evidenceQuery = useQuery<Evidence[], Error>({ queryKey: ["evidence"], queryFn: () => evidenceApi.listEvidence(), retry: false });
  const controlsQuery = useQuery<Control[], Error>({ queryKey: ["controls", "evidence-picker"], queryFn: () => controlsApi.list(), retry: false });
  const extractMutation = useMutation({ mutationFn: (id: string) => evidenceApi.extractEvidence(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["evidence"] }) });
  const uploadMutation = useMutation({
    mutationFn: ({ controlId, file }: { controlId: string; file: File }) => evidenceApi.uploadEvidence(controlId, file),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["evidence"] }); setUploadControl(""); },
  });

  const filteredEvidence = useMemo(() => (evidenceQuery.data ?? []).filter((item) => {
    const text = `${item.title} ${item.drive_file_name} ${item.control_ref ?? ""} ${item.control_name ?? ""}`.toLowerCase();
    return (!controlFilter || text.includes(controlFilter.toLowerCase())) && (!statusFilter || item.status === statusFilter);
  }), [controlFilter, evidenceQuery.data, statusFilter]);

  if (evidenceQuery.isLoading || controlsQuery.isLoading) return <div className="page-container evidence-page"><div className="page-header"><h2>Evidence Library</h2><p className="page-description">Google Drive evidence files and automated verification status.</p></div><div className="dashboard-state" role="status"><div className="loading-spinner" /><p>Loading evidence library...</p></div></div>;

  return (
    <div className="page-container evidence-page">
      <div className="page-header"><div><h2>Evidence Library</h2><p className="page-description">Google Drive evidence files and automated verification status.</p></div><div className="evidence-header-actions"><select aria-label="Upload evidence control" value={uploadControl} onChange={(event) => setUploadControl(event.target.value)}><option value="">Upload to control...</option>{(controlsQuery.data ?? []).map((control) => <option value={control.id} key={control.id}>{control.ref} · {control.name}</option>)}</select><button type="button" className="primary-btn" disabled={!uploadControl} onClick={() => fileInput.current?.click()}><Upload size={16} /> Upload evidence</button><input ref={fileInput} hidden type="file" onChange={(event) => { const file = event.target.files?.[0]; if (file && uploadControl) uploadMutation.mutate({ controlId: uploadControl, file }); event.target.value = ""; }} /></div></div>
      {evidenceQuery.error && <div className="dashboard-state dashboard-state-error" role="alert"><CircleAlert size={23} /><span>Evidence unavailable. {evidenceQuery.error.message}</span></div>}
      {uploadMutation.error && <p className="form-error">{uploadMutation.error.message}</p>}
      <div className="evidence-toolbar"><label className="toolbar-search"><Search size={15} /><input aria-label="Search evidence" placeholder="Search evidence or controls..." value={controlFilter} onChange={(event) => setControlFilter(event.target.value)} /></label><select aria-label="Filter evidence status" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as EvidenceStatus | "")}><option value="">All freshness</option><option value="current">Current</option><option value="stale">Stale</option><option value="missing">Missing</option></select><span className="control-count">{filteredEvidence.length} evidence items</span></div>
      {!evidenceQuery.error && filteredEvidence.length === 0 ? <div className="dashboard-empty"><FileText size={23} /><p>No evidence files match your filters. Link a Drive file or upload evidence to get started.</p></div> : <div className="evidence-list">{filteredEvidence.map((evidence) => <EvidenceCard key={evidence.id} evidence={evidence} onExtract={(id) => extractMutation.mutate(id)} extracting={extractMutation.isPending && extractMutation.variables === evidence.id} />)}</div>}
      {extractMutation.error && <p className="form-error">Extraction failed. {extractMutation.error.message}</p>}
      {(controlsQuery.data ?? []).length > 0 && <section className="evidence-link-section"><div className="section-heading"><div><h3>Attach an existing Drive file</h3><p>Choose a control, then search and link a file from Drive.</p></div></div><div className="evidence-control-grid">{controlsQuery.data?.map((control) => <button type="button" className="evidence-control-option" key={control.id} onClick={() => setPickerControl(control.id)}><Link2 size={16} /><span><strong>{control.ref}</strong><small>{control.name}</small></span><b>{control.evidence_count}</b></button>)}</div></section>}
      {pickerControl && <DrivePicker controlId={pickerControl} onClose={() => setPickerControl(null)} onLinked={() => { setPickerControl(null); queryClient.invalidateQueries({ queryKey: ["evidence"] }); }} />}
    </div>
  );
}
