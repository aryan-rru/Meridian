import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Edit3,
  Filter,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { controlsApi } from "../api/controls";
import { frameworksApi } from "../api/frameworks";
import type {
  Control,
  ControlCreate,
  ControlDetail,
  ControlStatus,
  CoverageLevel,
  Requirement,
} from "../types";

const STATUS_OPTIONS: ControlStatus[] = [
  "not_implemented",
  "partial",
  "implemented",
  "not_applicable",
];

type ControlForm = ControlCreate;
type SortKey = "ref" | "name" | "category" | "status" | "requirements_satisfied_count" | "frameworks_touched";

const emptyForm: ControlForm = {
  ref: "",
  name: "",
  description: "",
  category: "",
  owner: "",
  status: "not_implemented",
  implementation_notes: "",
};

function statusLabel(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function StatusBadge({ status }: { status: string }) {
  return <span className={`control-status-badge ${status}`}>{statusLabel(status)}</span>;
}

export function RequirementsPicker({
  requirements,
  selected,
  onChange,
}: {
  requirements: Requirement[];
  selected: Record<string, CoverageLevel>;
  onChange: (id: string, level?: CoverageLevel) => void;
}) {
  const [search, setSearch] = useState("");
  const filtered = requirements.filter((requirement) => {
    const haystack = `${requirement.code} ${requirement.title} ${requirement.category} ${requirement.framework_name}`.toLowerCase();
    return haystack.includes(search.toLowerCase());
  });
  const groups = filtered.reduce<Record<string, Requirement[]>>((result, requirement) => {
    (result[requirement.framework_key] ??= []).push(requirement);
    return result;
  }, {});

  return (
    <div className="requirement-picker">
      <div className="picker-heading">
        <div>
          <h4>Requirements answered</h4>
          <p>Select the requirements this control satisfies.</p>
        </div>
        <span className="picker-count">{Object.keys(selected).length} selected</span>
      </div>
      <label className="picker-search">
        <Search size={15} />
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search requirements..."
          aria-label="Search requirements"
        />
      </label>
      <div className="requirement-groups">
        {Object.entries(groups).map(([frameworkKey, items]) => (
          <fieldset className="requirement-group" key={frameworkKey}>
            <legend>
              <span className="framework-color-dot" style={{ backgroundColor: items[0].framework_color }} />
              {items[0].framework_name}
            </legend>
            {items.map((requirement) => {
              const coverage = selected[requirement.id];
              return (
                <div className={`requirement-option ${coverage ? "selected" : ""}`} key={requirement.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={Boolean(coverage)}
                      onChange={(event) =>
                        onChange(requirement.id, event.target.checked ? "full" : undefined)
                      }
                    />
                    <span className="requirement-check">{coverage && <Check size={13} />}</span>
                    <span className="requirement-copy">
                      <strong>{requirement.code}</strong>
                      <span>{requirement.title}</span>
                    </span>
                  </label>
                  {coverage && (
                    <select
                      value={coverage}
                      onChange={(event) =>
                        onChange(requirement.id, event.target.value as CoverageLevel)
                      }
                      aria-label={`${requirement.code} coverage level`}
                    >
                      <option value="full">Full</option>
                      <option value="partial">Partial</option>
                    </select>
                  )}
                </div>
              );
            })}
          </fieldset>
        ))}
        {filtered.length === 0 && <p className="picker-empty">No requirements match your search.</p>}
      </div>
    </div>
  );
}

function ControlModal({
  control,
  requirements,
  onClose,
  onSave,
  saving,
}: {
  control: Control | null;
  requirements: Requirement[];
  onClose: () => void;
  onSave: (form: ControlForm, selected: Record<string, CoverageLevel>) => Promise<void>;
  saving: boolean;
}) {
  const detailQuery = useQuery<ControlDetail, Error>({
    queryKey: ["control", control?.id],
    queryFn: () => controlsApi.get(control!.id),
    enabled: Boolean(control),
    retry: false,
  });
  const [form, setForm] = useState<ControlForm>(() =>
    control
      ? {
          ref: control.ref,
          name: control.name,
          description: control.description,
          category: control.category,
          owner: control.owner,
          status: control.status,
          implementation_notes: control.implementation_notes,
        }
      : emptyForm,
  );
  const [selected, setSelected] = useState<Record<string, CoverageLevel>>({});
  const [mappingEdited, setMappingEdited] = useState(false);
  const loadedDetail = detailQuery.data;
  const initialised = control ? detailQuery.isSuccess : true;

  if (control && detailQuery.isLoading) {
    return (
      <div className="modal-backdrop">
        <div className="control-modal" role="dialog" aria-modal="true" aria-label="Edit control">
          <div className="modal-loading">Loading control details...</div>
        </div>
      </div>
    );
  }

  if (control && !initialised) {
    return (
      <div className="modal-backdrop">
        <div className="control-modal" role="dialog" aria-modal="true" aria-label="Edit control">
          <div className="modal-loading" role="alert">Unable to load control details.</div>
          <button type="button" className="secondary-btn" onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }

  const effectiveSelected =
    control && loadedDetail && !mappingEdited
      ? Object.fromEntries(loadedDetail.requirements.map((item) => [item.id, item.coverage_level]))
      : selected;

  const updateField = (field: keyof ControlForm, value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <form
        className="control-modal"
        role="dialog"
        aria-modal="true"
        aria-label={control ? "Edit control" : "Create control"}
        onSubmit={async (event) => {
          event.preventDefault();
          await onSave(form, effectiveSelected);
        }}
      >
        <div className="modal-header">
          <div>
            <h3>{control ? "Edit control" : "Add control"}</h3>
            <p>Keep one clear control statement and map it to every requirement it answers.</p>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close dialog"><X size={18} /></button>
        </div>
        <div className="control-form-grid">
          <label>Reference<input required value={form.ref} onChange={(event) => updateField("ref", event.target.value)} placeholder="CTL-025" /></label>
          <label>Control name<input required value={form.name} onChange={(event) => updateField("name", event.target.value)} placeholder="Describe the control" /></label>
          <label>Category<input value={form.category} onChange={(event) => updateField("category", event.target.value)} placeholder="Access management" /></label>
          <label>Owner<input value={form.owner} onChange={(event) => updateField("owner", event.target.value)} placeholder="Team or role" /></label>
          <label>Status<select value={form.status} onChange={(event) => updateField("status", event.target.value)}>{STATUS_OPTIONS.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select></label>
          <label className="form-full-width">Description<textarea rows={2} value={form.description} onChange={(event) => updateField("description", event.target.value)} /></label>
          <label className="form-full-width">Implementation notes<textarea rows={2} value={form.implementation_notes} onChange={(event) => updateField("implementation_notes", event.target.value)} /></label>
        </div>
        <RequirementsPicker
          requirements={requirements}
          selected={effectiveSelected}
          onChange={(id, level) =>
            (setMappingEdited(true), setSelected((current) => {
              const next = { ...effectiveSelected, ...current };
              if (level) next[id] = level;
              else delete next[id];
              return next;
            }))
          }
        />
        <div className="modal-actions">
          <button type="button" className="secondary-btn" onClick={onClose}>Cancel</button>
          <button type="submit" className="primary-btn" disabled={saving || !form.ref.trim() || !form.name.trim()}>
            {saving ? "Saving..." : control ? "Save changes" : "Create control"}
          </button>
        </div>
      </form>
    </div>
  );
}

export function Controls() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ q: "", status: "", category: "" });
  const [sort, setSort] = useState<{ key: SortKey; direction: "asc" | "desc" }>({ key: "ref", direction: "asc" });
  const [editing, setEditing] = useState<Control | null | undefined>(undefined);
  const [deleteTarget, setDeleteTarget] = useState<Control | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const controlsQuery = useQuery<Control[], Error>({
    queryKey: ["controls", filters],
    queryFn: () => controlsApi.list(filters),
    retry: false,
  });
  const requirementsQuery = useQuery({
    queryKey: ["requirements"],
    queryFn: () => frameworksApi.listRequirements(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });

  const saveMutation = useMutation({
    mutationFn: async ({ control, form, selected }: { control: Control | null; form: ControlForm; selected: Record<string, CoverageLevel> }) => {
      const saved = control ? await controlsApi.update(control.id, form) : await controlsApi.create(form);
      await controlsApi.setRequirements(saved.id, {
        items: Object.entries(selected).map(([requirement_id, coverage_level]) => ({ requirement_id, coverage_level })),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["controls"] });
      await queryClient.invalidateQueries({ queryKey: ["control"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setEditing(undefined);
    },
    onError: (error: Error) => setErrorMessage(error.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => controlsApi.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["controls"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      setDeleteTarget(null);
    },
    onError: (error: Error) => setErrorMessage(error.message),
  });

  const controls = useMemo(() => {
    const items = [...(controlsQuery.data ?? [])];
    items.sort((left, right) => {
      const leftValue = left[sort.key];
      const rightValue = right[sort.key];
      const comparison =
        typeof leftValue === "number" && typeof rightValue === "number"
          ? leftValue - rightValue
          : String(leftValue).localeCompare(String(rightValue));
      return sort.direction === "asc" ? comparison : -comparison;
    });
    return items;
  }, [controlsQuery.data, sort]);

  const categories = [...new Set((controlsQuery.data ?? []).map((control) => control.category).filter(Boolean))];
  const changeSort = (key: SortKey) =>
    setSort((current) => ({ key, direction: current.key === key && current.direction === "asc" ? "desc" : "asc" }));
  const sortIcon = (key: SortKey) =>
    sort.key === key ? (sort.direction === "asc" ? <ChevronUp size={14} /> : <ChevronDown size={14} />) : null;

  return (
    <div className="page-container controls-page">
      <div className="page-header controls-page-header">
        <div>
          <h2>Control Library</h2>
          <p className="page-description">Maintain unified controls mapped across frameworks.</p>
        </div>
        <button type="button" className="primary-btn" onClick={() => { setErrorMessage(null); setEditing(null); }}><Plus size={16} /> Add control</button>
      </div>

      {errorMessage && <div className="inline-error" role="alert"><span>{errorMessage}</span><button type="button" onClick={() => setErrorMessage(null)} aria-label="Dismiss error"><X size={15} /></button></div>}

      <div className="controls-toolbar">
        <label className="toolbar-search"><Search size={16} /><input value={filters.q} onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))} placeholder="Search controls..." aria-label="Search controls" /></label>
        <label className="toolbar-select"><Filter size={15} /><select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">All statuses</option>{STATUS_OPTIONS.map((status) => <option key={status} value={status}>{statusLabel(status)}</option>)}</select></label>
        <label className="toolbar-select"><select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))}><option value="">All categories</option>{categories.map((category) => <option key={category} value={category}>{category}</option>)}</select></label>
        <span className="control-count">{controlsQuery.data?.length ?? 0} controls</span>
      </div>

      {controlsQuery.isLoading || requirementsQuery.isLoading ? (
        <div className="dashboard-state" role="status"><div className="loading-spinner" /><p>Loading controls...</p></div>
      ) : controlsQuery.error || requirementsQuery.error ? (
        <div className="dashboard-state dashboard-state-error" role="alert"><span>Unable to load the control library. {controlsQuery.error?.message || requirementsQuery.error?.message}</span></div>
      ) : controls.length === 0 ? (
        <div className="empty-panel"><Search size={22} /><strong>No controls found</strong><p>Try changing the filters or add your first control.</p></div>
      ) : (
        <div className="controls-table-wrap">
          <table className="controls-table">
            <thead><tr>
              {([["ref", "Reference"], ["name", "Control"], ["category", "Category"], ["status", "Status"], ["requirements_satisfied_count", "Requirements"], ["frameworks_touched", "Frameworks"]] as [SortKey, string][]).map(([key, label]) => <th key={key}><button type="button" onClick={() => changeSort(key)}>{label}{sortIcon(key)}</button></th>)}
              <th><span className="sr-only">Actions</span></th>
            </tr></thead>
            <tbody>{controls.map((control) => (
              <tr key={control.id}>
                <td className="control-ref">{control.ref}</td>
                <td><div className="control-name-cell"><strong>{control.name}</strong><span>{control.owner || "No owner assigned"}</span></div></td>
                <td>{control.category || "—"}</td>
                <td><StatusBadge status={control.status} /></td>
                <td><strong>{control.requirements_satisfied_count}</strong><span className="table-muted"> answered</span></td>
                <td><strong>{control.frameworks_touched}</strong><span className="table-muted"> frameworks</span></td>
                <td><div className="row-actions"><button type="button" className="icon-btn" onClick={() => { setErrorMessage(null); setEditing(control); }} aria-label={`Edit ${control.ref}`}><Edit3 size={15} /></button><button type="button" className="icon-btn danger-icon" onClick={() => setDeleteTarget(control)} aria-label={`Delete ${control.ref}`}><Trash2 size={15} /></button></div></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}

      {editing !== undefined && requirementsQuery.data && <ControlModal control={editing} requirements={requirementsQuery.data} onClose={() => setEditing(undefined)} saving={saveMutation.isPending} onSave={async (form, selected) => { setErrorMessage(null); await saveMutation.mutateAsync({ control: editing, form, selected }); }} />}

      {deleteTarget && <div className="modal-backdrop"><div className="confirm-modal" role="alertdialog" aria-modal="true" aria-label="Delete control confirmation"><h3>Delete {deleteTarget.ref}?</h3><p>This removes the control and its requirement mappings. This action cannot be undone.</p><div className="modal-actions"><button type="button" className="secondary-btn" onClick={() => setDeleteTarget(null)}>Cancel</button><button type="button" className="danger-btn" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(deleteTarget.id)}>{deleteMutation.isPending ? "Deleting..." : "Delete control"}</button></div></div></div>}
    </div>
  );
}
