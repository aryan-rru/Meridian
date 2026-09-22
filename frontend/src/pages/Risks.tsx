import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ChevronDown, ChevronUp, Edit3, Plus, Search, Trash2, X } from "lucide-react";
import { Link } from "react-router-dom";
import { risksApi } from "../api/risks";
import { settingsApi } from "../api/settings";
import type { Risk, RiskCreate, RiskStatus, RiskTreatment, ScoringConfig } from "../types";

const statuses: RiskStatus[] = ["open", "monitoring", "closed"];
const treatments: RiskTreatment[] = ["mitigate", "accept", "transfer", "avoid"];
const emptyForm: RiskCreate = {
  ref: "",
  title: "",
  description: "",
  category: "",
  owner: "",
  inherent_likelihood: 3,
  inherent_impact: 3,
  residual_likelihood: 2,
  residual_impact: 2,
  treatment: "mitigate",
  status: "open",
};

type SortKey = "ref" | "title" | "status" | "inherent_score" | "residual_score";

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function BandChip({ band }: { band: Risk["residual_band"] }) {
  return (
    <span className="risk-band-chip" style={{ borderColor: band.color, color: band.color }}>
      <i style={{ backgroundColor: band.color }} />{band.name}
    </span>
  );
}

export function ScaleSelect({
  name,
  value,
  labels,
  onChange,
}: {
  name: string;
  value: number;
  labels: Record<string, string>;
  onChange: (value: number) => void;
}) {
  return (
    <select aria-label={name} value={value} onChange={(event) => onChange(Number(event.target.value))}>
      {Array.from({ length: 10 }, (_, index) => index + 1).map((score) => (
        <option key={score} value={score}>{score} — {labels[String(score)] || `Level ${score}`}</option>
      ))}
    </select>
  );
}

function RiskModal({
  risk,
  config,
  onClose,
  onSave,
  saving,
}: {
  risk: Risk | null;
  config: ScoringConfig;
  onClose: () => void;
  onSave: (form: RiskCreate) => Promise<void>;
  saving: boolean;
}) {
  const [form, setForm] = useState<RiskCreate>(() =>
    risk
      ? {
          ref: risk.ref,
          title: risk.title,
          description: risk.description,
          category: risk.category,
          owner: risk.owner,
          inherent_likelihood: risk.inherent_likelihood,
          inherent_impact: risk.inherent_impact,
          residual_likelihood: risk.residual_likelihood,
          residual_impact: risk.residual_impact,
          treatment: risk.treatment,
          status: risk.status,
        }
      : emptyForm,
  );
  const update = (field: keyof RiskCreate, value: string | number) =>
    setForm((current) => ({ ...current, [field]: value }));
  const scale = (field: keyof RiskCreate, value: number) => update(field, value);

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form className="risk-modal" role="dialog" aria-modal="true" aria-label={risk ? "Edit risk" : "Create risk"} onSubmit={async (event) => { event.preventDefault(); await onSave(form); }}>
        <div className="modal-header">
          <div><h3>{risk ? "Edit risk" : "Add risk"}</h3><p>Score inherent exposure before controls and residual exposure after controls.</p></div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close dialog"><X size={18} /></button>
        </div>
        <div className="control-form-grid">
          <label>Reference<input required value={form.ref} onChange={(event) => update("ref", event.target.value)} placeholder="RISK-011" /></label>
          <label>Risk title<input required value={form.title} onChange={(event) => update("title", event.target.value)} placeholder="Describe what could go wrong" /></label>
          <label>Category<input value={form.category} onChange={(event) => update("category", event.target.value)} placeholder="Access" /></label>
          <label>Owner<input value={form.owner} onChange={(event) => update("owner", event.target.value)} placeholder="Team or role" /></label>
          <label>Status<select value={form.status} onChange={(event) => update("status", event.target.value)}>{statuses.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
          <label>Treatment<select value={form.treatment} onChange={(event) => update("treatment", event.target.value)}>{treatments.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
          <label className="form-full-width">Description<textarea rows={2} value={form.description} onChange={(event) => update("description", event.target.value)} /></label>
        </div>
        <div className="risk-score-form">
          <fieldset><legend>Inherent risk — before controls</legend><label>Likelihood<ScaleSelect name="Inherent likelihood" value={form.inherent_likelihood} labels={config.likelihood_labels} onChange={(value) => scale("inherent_likelihood", value)} /></label><label>Impact<ScaleSelect name="Inherent impact" value={form.inherent_impact} labels={config.impact_labels} onChange={(value) => scale("inherent_impact", value)} /></label></fieldset>
          <fieldset><legend>Residual risk — after controls</legend><label>Likelihood<ScaleSelect name="Residual likelihood" value={form.residual_likelihood} labels={config.likelihood_labels} onChange={(value) => scale("residual_likelihood", value)} /></label><label>Impact<ScaleSelect name="Residual impact" value={form.residual_impact} labels={config.impact_labels} onChange={(value) => scale("residual_impact", value)} /></label></fieldset>
        </div>
        <div className="modal-actions"><button type="button" className="secondary-btn" onClick={onClose}>Cancel</button><button type="submit" className="primary-btn" disabled={saving || !form.ref.trim() || !form.title.trim()}>{saving ? "Saving..." : risk ? "Save changes" : "Create risk"}</button></div>
      </form>
    </div>
  );
}

export function Risks() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ q: "", status: "", band: "", category: "" });
  const [sort, setSort] = useState<{ key: SortKey; direction: "asc" | "desc" }>({ key: "residual_score", direction: "desc" });
  const [editing, setEditing] = useState<Risk | null | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Risk | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const risksQuery = useQuery<Risk[], Error>({ queryKey: ["risks", filters], queryFn: () => risksApi.list(filters), retry: false });
  const settingsQuery = useQuery<ScoringConfig, Error>({ queryKey: ["settings"], queryFn: settingsApi.getSettings, staleTime: 5 * 60 * 1000, retry: false });
  const saveMutation = useMutation({
    mutationFn: async ({ risk, form }: { risk: Risk | null; form: RiskCreate }) => risk ? risksApi.update(risk.id, form) : risksApi.create(form),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["risks"] }); await queryClient.invalidateQueries({ queryKey: ["dashboard"] }); setEditing(undefined); },
    onError: (error: Error) => setErrorMessage(error.message),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: string) => risksApi.delete(id),
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ["risks"] }); await queryClient.invalidateQueries({ queryKey: ["dashboard"] }); setDeleteTarget(null); },
    onError: (error: Error) => setErrorMessage(error.message),
  });
  const risks = useMemo(() => {
    const items = [...(risksQuery.data ?? [])];
    items.sort((left, right) => {
      const a = left[sort.key];
      const b = right[sort.key];
      const comparison = typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
      return sort.direction === "asc" ? comparison : -comparison;
    });
    return items;
  }, [risksQuery.data, sort]);
  const categories = [...new Set((risksQuery.data ?? []).map((risk) => risk.category).filter(Boolean))];
  const changeSort = (key: SortKey) => setSort((current) => ({ key, direction: current.key === key && current.direction === "asc" ? "desc" : "asc" }));
  const sortIcon = (key: SortKey) => sort.key === key ? (sort.direction === "asc" ? <ChevronUp size={14} /> : <ChevronDown size={14} />) : null;

  return (
    <div className="page-container risks-page">
      <div className="page-header controls-page-header"><div><h2>Risk Register</h2><p className="page-description">Inherent and residual risk tracking with assurance flags.</p></div><button type="button" className="primary-btn" onClick={() => { setErrorMessage(null); setEditing(null); }}><Plus size={16} /> Add risk</button></div>
      {errorMessage && <div className="inline-error" role="alert"><span>{errorMessage}</span><button type="button" onClick={() => setErrorMessage(null)} aria-label="Dismiss error"><X size={15} /></button></div>}
      <div className="controls-toolbar"><label className="toolbar-search"><Search size={16} /><input aria-label="Search risks" value={filters.q} onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} placeholder="Search risks..." /></label><label className="toolbar-select"><select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option>{statuses.map((status) => <option key={status} value={status}>{label(status)}</option>)}</select></label><label className="toolbar-select"><select value={filters.band} onChange={(event) => setFilters((current) => ({ ...current, band: event.target.value }))}><option value="">All bands</option>{settingsQuery.data?.risk_bands.map((band) => <option key={band.name} value={band.name}>{band.name}</option>)}</select></label><label className="toolbar-select"><select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label><span className="control-count">{risksQuery.data?.length ?? 0} risks</span></div>
      {risksQuery.isLoading || settingsQuery.isLoading ? <div className="dashboard-state" role="status"><div className="loading-spinner" /><p>Loading risk register...</p></div> : risksQuery.error || settingsQuery.error ? <div className="dashboard-state dashboard-state-error" role="alert">Unable to load risks. {risksQuery.error?.message || settingsQuery.error?.message}</div> : risks.length === 0 ? <div className="empty-panel"><Search size={22} /><strong>No risks found</strong><p>Try changing the filters or add a new risk.</p></div> : (
        <div className="risks-table-wrap"><table className="risks-table"><thead><tr>{([["ref", "Reference"], ["title", "Risk"], ["status", "Status"], ["inherent_score", "Inherent"], ["residual_score", "Residual"]] as [SortKey, string][]).map(([key, text]) => <th key={key}><button type="button" onClick={() => changeSort(key)}>{text}{sortIcon(key)}</button></th>)}<th><span className="sr-only">Actions</span></th></tr></thead><tbody>{risks.map((risk) => <tr key={risk.id}><td><Link to={`/risks/${risk.id}`} className="risk-ref">{risk.ref}</Link></td><td><div className="risk-name-cell"><strong>{risk.title}</strong><span>{risk.category || "Uncategorized"} · {risk.owner || "No owner"}</span></div></td><td><span className={`risk-status-badge ${risk.status}`}>{label(risk.status)}</span></td><td><div className="risk-score-cell"><strong>{risk.inherent_score}</strong><BandChip band={risk.inherent_band} /></div></td><td><div className="risk-score-cell"><strong>{risk.residual_score}</strong><BandChip band={risk.residual_band} />{risk.assurance.flag === "unsupported_residual" && <span className="assurance-flag" title={risk.assurance.message || "Residual risk may be unsupported"}><AlertTriangle size={14} /> Unearned residual</span>}</div></td><td><div className="row-actions"><button type="button" className="icon-btn" onClick={() => { setErrorMessage(null); setEditing(risk); }} aria-label={`Edit ${risk.ref}`}><Edit3 size={15} /></button><button type="button" className="icon-btn danger-icon" onClick={() => setDeleteTarget(risk)} aria-label={`Delete ${risk.ref}`}><Trash2 size={15} /></button></div></td></tr>)}</tbody></table></div>
      )}
      {editing !== undefined && settingsQuery.data && <RiskModal risk={editing} config={settingsQuery.data} onClose={() => setEditing(undefined)} saving={saveMutation.isPending} onSave={async (form) => { setErrorMessage(null); await saveMutation.mutateAsync({ risk: editing, form }); }} />}
      {deleteTarget && <div className="modal-backdrop"><div className="confirm-modal" role="alertdialog" aria-modal="true" aria-label="Delete risk confirmation"><h3>Delete {deleteTarget.ref}?</h3><p>This removes the risk and its mitigating-control mappings. This action cannot be undone.</p><div className="modal-actions"><button type="button" className="secondary-btn" onClick={() => setDeleteTarget(null)}>Cancel</button><button type="button" className="danger-btn" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(deleteTarget.id)}>{deleteMutation.isPending ? "Deleting..." : "Delete risk"}</button></div></div></div>}
    </div>
  );
}
