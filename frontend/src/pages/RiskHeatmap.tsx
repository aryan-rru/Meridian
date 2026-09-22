import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CircleAlert, Info, X } from "lucide-react";
import { Link } from "react-router-dom";
import { risksApi } from "../api/risks";
import type { HeatmapCell, HeatmapRead } from "../types";

type HeatmapBasis = "inherent" | "residual";

function HeatmapLoading({ basis }: { basis: HeatmapBasis }) {
  return (
    <div className="page-container risk-heatmap-page">
      <div className="page-header">
        <h2>5×5 Risk Heatmap</h2>
        <p className="page-description">Likelihood × Impact matrix showing {basis} risk distribution.</p>
      </div>
      <div className="dashboard-state" role="status"><div className="loading-spinner" /><p>Loading risk heatmap...</p></div>
    </div>
  );
}

function HeatmapLegend() {
  return (
    <div className="risk-heatmap-legend" aria-label="Risk band legend">
      <span><i className="risk-legend-swatch low" /> Low</span>
      <span><i className="risk-legend-swatch medium" /> Medium</span>
      <span><i className="risk-legend-swatch high" /> High</span>
      <span><i className="risk-legend-swatch critical" /> Critical</span>
      <span><Info size={14} /> Click a cell to see its risks</span>
    </div>
  );
}

function CellDetails({ cell, basis, onClose }: { cell: HeatmapCell; basis: HeatmapBasis; onClose: () => void }) {
  return (
    <aside className="risk-cell-detail" role="dialog" aria-modal="true" aria-label={`Risks at likelihood ${cell.likelihood}, impact ${cell.impact}`}>
      <div className="risk-cell-detail-header">
        <div>
          <span className="detail-label">{basis} risk cell</span>
          <h3>Likelihood {cell.likelihood} × Impact {cell.impact}</h3>
          <p><strong>{cell.count}</strong> {cell.count === 1 ? "risk" : "risks"} · score {cell.score} · {cell.band_name}</p>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close risk cell details"><X size={18} /></button>
      </div>
      {cell.risks.length === 0 ? (
        <p className="detail-muted">No risks are recorded in this cell.</p>
      ) : (
        <div className="risk-cell-risk-list">
          {cell.risks.map((risk) => (
            <Link to={`/risks/${risk.id}`} className="risk-cell-risk" key={risk.id}>
              <div>
                <strong>{risk.ref}</strong>
                <span>{risk.title}</span>
              </div>
              <div className="risk-cell-risk-score">
                <b>{basis === "inherent" ? risk.inherent_score : risk.residual_score}</b>
                {risk.assurance_flag === "unsupported_residual" && <AlertTriangle size={14} aria-label="Unearned residual" />}
              </div>
            </Link>
          ))}
        </div>
      )}
    </aside>
  );
}

export function RiskHeatmap() {
  const [basis, setBasis] = useState<HeatmapBasis>("residual");
  const [selectedCell, setSelectedCell] = useState<HeatmapCell | null>(null);
  const query = useQuery<HeatmapRead, Error>({
    queryKey: ["risk-heatmap", basis],
    queryFn: () => risksApi.getHeatmap(basis),
    retry: false,
  });

  if (query.isLoading) return <HeatmapLoading basis={basis} />;

  return (
    <div className="page-container risk-heatmap-page">
      <div className="page-header risk-heatmap-header">
        <div>
          <h2>5×5 Risk Heatmap</h2>
          <p className="page-description">Likelihood × Impact matrix showing {basis} risk distribution.</p>
        </div>
        <div className="segmented-control" role="group" aria-label="Risk heatmap basis">
          <button type="button" className={basis === "inherent" ? "active" : ""} onClick={() => { setBasis("inherent"); setSelectedCell(null); }}>Inherent</button>
          <button type="button" className={basis === "residual" ? "active" : ""} onClick={() => { setBasis("residual"); setSelectedCell(null); }}>Residual</button>
        </div>
      </div>

      {query.error || !query.data ? (
        <div className="dashboard-state dashboard-state-error" role="alert">
          <CircleAlert size={23} /><span>Risk heatmap unavailable. {query.error?.message || "No heatmap data was returned."}</span>
        </div>
      ) : (
        <>
          <div className="risk-heatmap-summary">
            <div><strong>{query.data.total_risks}</strong><span>Total risks</span></div>
            <div><strong>{query.data.matrix_size} × {query.data.matrix_size}</strong><span>Scoring matrix</span></div>
            <div><strong>{basis === "inherent" ? "Before controls" : "After controls"}</strong><span>Displayed basis</span></div>
          </div>
          <HeatmapLegend />
          <section className="risk-heatmap-card" aria-label={`${basis} risk matrix`}>
            <div className="risk-heatmap-axis-y">Likelihood</div>
            <div className="risk-heatmap-grid">
              <div className="risk-heatmap-corner" />
              {query.data.impact_labels.map((label) => <div className="risk-heatmap-axis-label" key={label.value}>{label.value}<small>{label.label}</small></div>)}
              {query.data.rows.map((row) => (
                <div className="risk-heatmap-row" key={row.likelihood}>
                  <div className="risk-heatmap-axis-label y"><strong>{row.likelihood}</strong><small>{row.likelihood_label}</small></div>
                  {row.cells.map((cell) => (
                    <button
                      type="button"
                      className="risk-heatmap-cell"
                      style={{ backgroundColor: `${cell.band_color}30`, borderColor: cell.band_color }}
                      key={`${cell.likelihood}-${cell.impact}`}
                      aria-label={`Likelihood ${cell.likelihood}, Impact ${cell.impact}, score ${cell.score}, ${cell.band_name}, ${cell.count} ${cell.count === 1 ? "risk" : "risks"}`}
                      onClick={() => setSelectedCell(cell)}
                    >
                      <strong>{cell.count || "·"}</strong>
                      <span>{cell.score}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
            <div className="risk-heatmap-axis-x">Impact →</div>
          </section>
          <div className="risk-heatmap-footnote"><Info size={14} /> Likelihood is shown from low to high; impact runs from 1 to {query.data.matrix_size}. Cell colour reflects the configured risk band.</div>
          {selectedCell && <CellDetails cell={selectedCell} basis={basis} onClose={() => setSelectedCell(null)} />}
        </>
      )}
    </div>
  );
}
