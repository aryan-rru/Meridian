import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CircleAlert, Plus, Save, Trash2 } from "lucide-react";
import { settingsApi } from "../api/settings";
import { useToast } from "../components/feedback/Toast";
import type { RiskBand, ScoringConfig, ScoringConfigUpdate, ScoreMethod } from "../types";

function SettingsLoading() {
  return <div className="page-container settings-page"><div className="page-header"><h2>Settings</h2><p className="page-description">Configure risk formulas, bands, labels, and matrix size.</p></div><div className="dashboard-state" role="status"><div className="loading-spinner" /><p>Loading settings...</p></div></div>;
}

function cloneConfig(config: ScoringConfig): ScoringConfig {
  return { ...config, weights: { ...config.weights }, remediation_weights: { ...config.remediation_weights }, likelihood_labels: { ...config.likelihood_labels }, impact_labels: { ...config.impact_labels }, risk_bands: config.risk_bands.map((band) => ({ ...band })) };
}

export function Settings() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const query = useQuery<ScoringConfig, Error>({ queryKey: ["settings"], queryFn: settingsApi.getSettings, retry: false });
  const [form, setForm] = useState<ScoringConfig | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (payload: ScoringConfigUpdate) => settingsApi.updateSettings(payload),
    onSuccess: (data) => { setForm(cloneConfig(data)); setMessage("Settings saved. Scores and derived views will use the new configuration."); showToast("Settings saved successfully."); setValidationError(null); queryClient.setQueryData(["settings"], data); },
    onError: (error: Error) => showToast(`Settings could not be saved. ${error.message}`, "error"),
  });

  useEffect(() => { if (query.data && !form) setForm(cloneConfig(query.data)); }, [form, query.data]);

  if (query.isLoading || !form) return <SettingsLoading />;
  if (query.error) return <div className="page-container settings-page"><div className="page-header"><h2>Settings</h2><p className="page-description">Configure risk formulas, bands, labels, and matrix size.</p></div><div className="dashboard-state dashboard-state-error" role="alert"><CircleAlert size={23} /> Settings unavailable. {query.error.message}</div></div>;

  const scale = Array.from({ length: form.matrix_size }, (_, index) => String(index + 1));
  const updateLabel = (kind: "likelihood_labels" | "impact_labels", key: string, value: string) => setForm((current) => current ? { ...current, [kind]: { ...current[kind], [key]: value } } : current);
  const updateBand = (index: number, field: keyof RiskBand, value: string) => setForm((current) => current ? { ...current, risk_bands: current.risk_bands.map((band, bandIndex) => bandIndex === index ? { ...band, [field]: field === "min" || field === "max" ? Number(value) : value } : band) } : current);
  const validate = () => {
    if (form.risk_bands.length === 0) return "Add at least one risk band.";
    const ordered = [...form.risk_bands].sort((a, b) => a.min - b.min);
    if (ordered[0].min !== 1 || ordered[ordered.length - 1].max !== form.max_possible_score) return `Risk bands must cover the full score range from 1 to ${form.max_possible_score}.`;
    for (let index = 0; index < ordered.length; index += 1) if (ordered[index].min > ordered[index].max || (index > 0 && ordered[index].min !== ordered[index - 1].max + 1)) return "Risk bands must be contiguous and non-overlapping.";
    if (scale.some((key) => !form.likelihood_labels[key]?.trim() || !form.impact_labels[key]?.trim())) return "Every likelihood and impact value needs a label.";
    return null;
  };
  const save = () => { const error = validate(); if (error) { setValidationError(error); setMessage(null); return; } setMessage(null); mutation.mutate({ matrix_size: form.matrix_size, score_method: form.score_method, weights: form.weights, likelihood_labels: form.likelihood_labels, impact_labels: form.impact_labels, risk_bands: form.risk_bands, remediation_weights: form.remediation_weights, evidence_stale_after_days: form.evidence_stale_after_days }); };
  const addBand = () => setForm((current) => current ? { ...current, risk_bands: [...current.risk_bands, { name: "New band", min: current.max_possible_score, max: current.max_possible_score, color: "#64748b" }] } : current);

  return (
    <div className="page-container settings-page">
      <div className="page-header settings-header"><div><h2>Settings</h2><p className="page-description">Configure risk formulas, bands, labels, and matrix size.</p></div><button type="button" className="primary-btn" onClick={save} disabled={mutation.isPending}><Save size={16} /> {mutation.isPending ? "Saving..." : "Save settings"}</button></div>
      {validationError && <div className="settings-alert error" role="alert"><AlertTriangle size={17} />{validationError}</div>}
      {mutation.error && <div className="settings-alert error" role="alert"><CircleAlert size={17} />Settings could not be saved. {mutation.error.message}</div>}
      {message && <div className="settings-alert success" role="status">{message}</div>}
      <div className="settings-grid">
        <section className="settings-card"><h3>Scoring method</h3><p>Changing this re-derives every risk score and band.</p><label>Score method<select value={form.score_method} onChange={(event) => setForm({ ...form, score_method: event.target.value as ScoreMethod })}><option value="multiply">Multiply (likelihood × impact)</option><option value="add">Add (likelihood + impact)</option><option value="weighted">Weighted score</option></select></label><div className="settings-two-fields"><label>Likelihood weight<input type="number" min="0" step="0.1" value={form.weights.wL} onChange={(event) => setForm({ ...form, weights: { ...form.weights, wL: Number(event.target.value) } })} /></label><label>Impact weight<input type="number" min="0" step="0.1" value={form.weights.wI} onChange={(event) => setForm({ ...form, weights: { ...form.weights, wI: Number(event.target.value) } })} /></label></div><label>Matrix size<select value={form.matrix_size} onChange={(event) => setForm({ ...form, matrix_size: Number(event.target.value) })}><option value={3}>3 × 3</option><option value={4}>4 × 4</option><option value={5}>5 × 5</option><option value={6}>6 × 6</option><option value={10}>10 × 10</option></select></label><label>Evidence stale after (days)<input type="number" min="1" value={form.evidence_stale_after_days} onChange={(event) => setForm({ ...form, evidence_stale_after_days: Number(event.target.value) })} /></label></section>
        <section className="settings-card"><h3>Likelihood labels</h3><p>These words appear beside score selectors and heatmap axes.</p>{scale.map((key) => <label className="settings-inline-field" key={key}><span>{key}</span><input aria-label={`Likelihood ${key} label`} value={form.likelihood_labels[key] ?? ""} onChange={(event) => updateLabel("likelihood_labels", key, event.target.value)} /></label>)}</section>
        <section className="settings-card"><h3>Impact labels</h3><p>Use plain-English labels your team understands.</p>{scale.map((key) => <label className="settings-inline-field" key={key}><span>{key}</span><input aria-label={`Impact ${key} label`} value={form.impact_labels[key] ?? ""} onChange={(event) => updateLabel("impact_labels", key, event.target.value)} /></label>)}</section>
        <section className="settings-card settings-card-wide"><div className="settings-section-header"><div><h3>Risk bands</h3><p>Bands must cover scores 1 through {form.max_possible_score} without gaps or overlaps.</p></div><button type="button" className="secondary-btn" onClick={addBand}><Plus size={15} /> Add band</button></div><div className="settings-band-list">{form.risk_bands.map((band, index) => <div className="settings-band-row" key={`${index}-${band.name}`}><input aria-label={`Band ${index + 1} name`} value={band.name} onChange={(event) => updateBand(index, "name", event.target.value)} /><input aria-label={`Band ${index + 1} minimum`} type="number" min="1" value={band.min} onChange={(event) => updateBand(index, "min", event.target.value)} /><span>to</span><input aria-label={`Band ${index + 1} maximum`} type="number" min="1" value={band.max} onChange={(event) => updateBand(index, "max", event.target.value)} /><input aria-label={`Band ${index + 1} color`} type="color" value={band.color} onChange={(event) => updateBand(index, "color", event.target.value)} /><button type="button" className="icon-btn danger-icon" aria-label={`Remove band ${band.name}`} onClick={() => setForm({ ...form, risk_bands: form.risk_bands.filter((_, bandIndex) => bandIndex !== index) })}><Trash2 size={15} /></button></div>)}</div></section>
        <section className="settings-card"><h3>Remediation weights</h3><p>Control how risk and requirement leverage affect ranking.</p><label>Risk weight<input type="number" min="0" step="0.1" value={form.remediation_weights.W_RISK} onChange={(event) => setForm({ ...form, remediation_weights: { ...form.remediation_weights, W_RISK: Number(event.target.value) } })} /></label><label>Requirement weight<input type="number" min="0" step="0.1" value={form.remediation_weights.W_REQ} onChange={(event) => setForm({ ...form, remediation_weights: { ...form.remediation_weights, W_REQ: Number(event.target.value) } })} /></label></section>
      </div>
    </div>
  );
}
