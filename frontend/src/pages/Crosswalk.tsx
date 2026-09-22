import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, Circle, Search } from "lucide-react";
import { derivedApi } from "../api/derived";
import type { CrosswalkRead, CrosswalkRow } from "../types";

function statusLabel(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function CrosswalkLoading() {
  return (
    <div className="page-container crosswalk-page">
      <div className="page-header">
        <h2>Crosswalk Matrix</h2>
        <p className="page-description">Loading controls and framework requirements...</p>
      </div>
      <div className="dashboard-state" role="status">
        <div className="loading-spinner" />
        <p>Loading crosswalk matrix...</p>
      </div>
    </div>
  );
}

function CrosswalkError({ message }: { message: string }) {
  return (
    <div className="dashboard-state dashboard-state-error" role="alert">
      <strong>Crosswalk unavailable</strong>
      <span>{message}</span>
    </div>
  );
}

function MatrixCell({
  row,
  requirementId,
  code,
  title,
}: {
  row: CrosswalkRow;
  requirementId: string;
  code: string;
  title: string;
}) {
  const mapping = row.cells[requirementId];
  const label = mapping
    ? `${row.ref} satisfies ${code} with ${mapping.coverage_level} coverage`
    : `${row.ref} does not satisfy ${code}`;

  return (
    <td className={`crosswalk-cell ${mapping ? mapping.coverage_level : "empty"}`}>
      <span className="crosswalk-cell-button" title={`${label}: ${title}`} aria-label={label}>
        {mapping ? <Check size={15} /> : <Circle size={7} />}
      </span>
    </td>
  );
}

function MatrixTable({ data, rows }: { data: CrosswalkRead; rows: CrosswalkRow[] }) {
  const groups = data.column_groups.map((group) => ({
    ...group,
    framework_color: group.framework_color ?? group.color,
    columns: group.columns ?? group.requirements ?? [],
  }));

  return (
    <div className="crosswalk-table-wrap">
      <table className="crosswalk-table">
        <thead>
          <tr className="crosswalk-framework-row">
            <th className="crosswalk-sticky-column" rowSpan={2}>Control</th>
            {groups.map((group) => (
              <th
                key={group.framework_key}
                colSpan={group.columns.length}
                style={{ borderTopColor: group.framework_color }}
                className="crosswalk-framework-heading"
              >
                <span className="framework-color-dot" style={{ backgroundColor: group.framework_color }} />
                {group.framework_name}
              </th>
            ))}
            <th className="crosswalk-leverage-heading" rowSpan={2}>Leverage</th>
          </tr>
          <tr className="crosswalk-requirement-row">
            {groups.flatMap((group) =>
              group.columns.map((column) => (
                <th key={column.requirement_id} title={column.title}>
                  <span>{column.code}</span>
                  <small>{column.category}</small>
                </th>
              )),
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.control_id}>
              <th className="crosswalk-sticky-column crosswalk-control-cell">
                <span className="crosswalk-control-ref">{row.ref}</span>
                <span className="crosswalk-control-name">{row.name}</span>
                <span className={`crosswalk-status ${row.status}`}>{statusLabel(row.status)}</span>
              </th>
              {groups.flatMap((group) =>
                group.columns.map((column) => (
                  <MatrixCell
                    key={`${row.control_id}-${column.requirement_id}`}
                    row={row}
                    requirementId={column.requirement_id}
                    code={column.code}
                    title={column.title}
                  />
                )),
              )}
              <td className="crosswalk-leverage-cell">
                <strong>{row.requirements_satisfied_count}</strong>
                <span>{row.frameworks_touched} fw</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Crosswalk() {
  const [search, setSearch] = useState("");
  const { data, isLoading, error } = useQuery<CrosswalkRead, Error>({
    queryKey: ["crosswalk"],
    queryFn: derivedApi.getCrosswalk,
    retry: false,
  });

  const rows = useMemo(() => {
    if (!data) return [];
    const query = search.trim().toLowerCase();
    if (!query) return data.rows;
    return data.rows.filter((row) =>
      `${row.ref} ${row.name} ${row.category}`.toLowerCase().includes(query),
    );
  }, [data, search]);

  if (isLoading) return <CrosswalkLoading />;
  if (error) return <CrosswalkError message={error.message} />;
  if (!data) return <CrosswalkError message="No crosswalk data was returned." />;

  return (
    <div className="page-container crosswalk-page">
      <div className="page-header">
        <h2>Crosswalk Matrix</h2>
        <p className="page-description">
          See which controls answer requirements across ISO 27001, SOC 2, and NIST CSF.
        </p>
      </div>

      <div className="crosswalk-summary" aria-label="Crosswalk summary">
        <div><strong>{data.summary.total_controls ?? data.summary.control_count}</strong><span>Controls</span></div>
        <div><strong>{data.summary.total_requirements ?? data.summary.requirement_count}</strong><span>Requirements</span></div>
        <div><strong>{data.summary.total_mappings ?? data.summary.mapping_count}</strong><span>Mappings</span></div>
        <div><strong>{(data.summary.average_leverage ?? data.summary.average_requirements_per_control ?? 0).toFixed(1)}</strong><span>Average leverage</span></div>
      </div>

      <label className="crosswalk-search">
        <Search size={16} />
        <input
          aria-label="Search controls in crosswalk"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search controls by reference, name, or category..."
        />
      </label>

      {rows.length === 0 ? (
        <div className="empty-panel">
          <Search size={22} />
          <strong>No controls match your search.</strong>
          <p>Try a different reference, name, or category.</p>
        </div>
      ) : (
        <MatrixTable data={data} rows={rows} />
      )}

      <div className="crosswalk-legend" aria-label="Crosswalk legend">
        <span><i className="crosswalk-legend-dot full"><Check size={11} /></i> Full coverage</span>
        <span><i className="crosswalk-legend-dot partial"><Check size={11} /></i> Partial coverage</span>
        <span><i className="crosswalk-legend-dot empty"><Circle size={6} /></i> No mapping</span>
      </div>
    </div>
  );
}
