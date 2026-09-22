import { useQuery } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  FileCheck2,
  ShieldCheck,
  Target,
} from "lucide-react";
import { Link } from "react-router-dom";
import { derivedApi } from "../api/derived";
import type { DashboardSummary } from "../types";

function formatStatus(status: string) {
  return status.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function DashboardLoading() {
  return (
    <div className="page-container dashboard-page">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p className="page-description">Loading your workspace summary...</p>
      </div>
      <div className="dashboard-state" role="status">
        <div className="loading-spinner" />
        <p>Loading dashboard summary...</p>
      </div>
    </div>
  );
}

function DashboardError({ message }: { message: string }) {
  return (
    <div className="dashboard-state dashboard-state-error" role="alert">
      <CircleAlert size={24} />
      <div>
        <strong>Dashboard unavailable</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}

export function Dashboard() {
  const { data, isLoading, error } = useQuery<DashboardSummary, Error>({
    queryKey: ["dashboard", "summary"],
    queryFn: derivedApi.getDashboardSummary,
    retry: false,
  });

  if (isLoading) return <DashboardLoading />;
  if (error) return <DashboardError message={error.message} />;
  if (!data) return <DashboardError message="No dashboard data was returned." />;

  const implemented = data.controls.by_status.implemented ?? 0;
  const partial = data.controls.by_status.partial ?? 0;
  const notImplemented = data.controls.by_status.not_implemented ?? 0;
  const evidenceCurrent = data.evidence.by_status.current ?? 0;
  const evidenceStale = data.evidence.by_status.stale ?? 0;
  const evidenceMissing = data.evidence.by_status.missing ?? 0;
  const evidenceFreshness =
    data.evidence.total > 0 ? Math.round((evidenceCurrent / data.evidence.total) * 100) : 0;

  return (
    <div className="page-container dashboard-page">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p className="page-description">
          A current view of control health, framework coverage, risk, and evidence.
        </p>
      </div>

      <section className="dashboard-summary-grid" aria-label="Compliance summary">
        <article className="dashboard-card control-summary-card">
          <div className="dashboard-card-heading">
            <span>Control status</span>
            <ShieldCheck size={18} />
          </div>
          <div className="control-summary-content">
            <div
              className="control-donut"
              role="img"
              style={{ "--control-progress": `${data.controls.implemented_percent}%` } as CSSProperties}
              aria-label={`${data.controls.implemented_percent}% of controls implemented`}
            >
              <strong>{data.controls.implemented_percent}%</strong>
              <span>implemented</span>
            </div>
            <div className="status-legend">
              <span><i className="legend-dot implemented" />{implemented} Implemented</span>
              <span><i className="legend-dot partial" />{partial} Partial</span>
              <span><i className="legend-dot not-implemented" />{notImplemented} Not implemented</span>
            </div>
          </div>
          <Link to="/controls" className="dashboard-card-link">View controls <ArrowRight size={14} /></Link>
        </article>

        <article className="dashboard-card metric-card">
          <div className="dashboard-card-heading"><span>Framework coverage</span><Target size={18} /></div>
          <strong className="metric-value">{data.coverage.totals.coverage_percent}%</strong>
          <span className="metric-label">{data.coverage.totals.covered} of {data.coverage.totals.total_requirements} requirements covered</span>
          <div className="metric-subline">{data.coverage.totals.partial} partial · {data.coverage.totals.gap} gaps</div>
          <Link to="/coverage" className="dashboard-card-link">Open coverage <ArrowRight size={14} /></Link>
        </article>

        <article className="dashboard-card metric-card">
          <div className="dashboard-card-heading"><span>Coverage gaps</span><AlertTriangle size={18} /></div>
          <strong className="metric-value warning">{data.gaps.gap_count}</strong>
          <span className="metric-label">requirements with no mapped control</span>
          <div className="metric-subline">{data.gaps.partial_count} partially covered</div>
          <Link to="/coverage" className="dashboard-card-link">Review gaps <ArrowRight size={14} /></Link>
        </article>

        <article className="dashboard-card metric-card">
          <div className="dashboard-card-heading"><span>Evidence freshness</span><FileCheck2 size={18} /></div>
          <strong className="metric-value">{evidenceFreshness}%</strong>
          <span className="metric-label">{evidenceCurrent} of {data.evidence.total} records current</span>
          <div className="metric-subline">{evidenceStale} stale · {evidenceMissing} missing</div>
          <Link to="/evidence" className="dashboard-card-link">Open evidence <ArrowRight size={14} /></Link>
        </article>

        <article className="dashboard-card metric-card">
          <div className="dashboard-card-heading"><span>Residual risk warnings</span><CircleAlert size={18} /></div>
          <strong className="metric-value danger">{data.risks.unsupported_residual_count}</strong>
          <span className="metric-label">risks with unsupported residual claims</span>
          <div className="metric-subline">{data.risks.open} open of {data.risks.total} total risks</div>
          <Link to="/risks" className="dashboard-card-link">Review risks <ArrowRight size={14} /></Link>
        </article>
      </section>

      <section className="dashboard-section">
        <div className="section-heading">
          <div><h3>Coverage by framework</h3><p>See where each framework is strongest and where work remains.</p></div>
          <Link to="/coverage" className="text-link">View heatmap <ArrowRight size={14} /></Link>
        </div>
        <div className="framework-card-grid">
          {data.coverage.frameworks.map((framework) => (
            <div className="framework-card" key={framework.framework_key}>
              <div className="framework-card-title">
                <span className="framework-color-dot" style={{ backgroundColor: framework.color }} />
                <strong>{framework.framework_name}</strong>
                <span>{framework.coverage_percent}%</span>
              </div>
              <div className="coverage-progress"><span style={{ width: `${framework.coverage_percent}%`, backgroundColor: framework.color }} /></div>
              <div className="framework-card-meta">{framework.covered_count} covered · {framework.partial_count} partial · {framework.gap_count} gaps</div>
            </div>
          ))}
        </div>
      </section>

      <div className="dashboard-two-column">
        <section className="dashboard-section dashboard-panel">
          <div className="section-heading">
            <div><h3>Top residual risks</h3><p>Highest remaining exposure after controls.</p></div>
            <Link to="/risks" className="text-link">All risks <ArrowRight size={14} /></Link>
          </div>
          {data.risks.top_by_residual.length === 0 ? (
            <div className="dashboard-empty">No risks recorded for this workspace.</div>
          ) : (
            <div className="dashboard-list">
              {data.risks.top_by_residual.map((risk) => (
                <Link to={`/risks/${risk.id}`} className="dashboard-list-item" key={risk.id}>
                  <div className="list-item-main"><strong>{risk.ref}</strong><span>{risk.title}</span></div>
                  <div className="risk-score" style={{ borderColor: risk.residual_band.color, color: risk.residual_band.color }}>
                    <strong>{risk.residual_score}</strong><small>{risk.residual_band.name}</small>
                  </div>
                  {risk.assurance.flag && <span className="assurance-warning" title="Unsupported residual assurance">!</span>}
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="dashboard-section dashboard-panel">
          <div className="section-heading">
            <div><h3>Top remediation priorities</h3><p>Controls with the greatest risk and requirement leverage.</p></div>
            <Link to="/remediation" className="text-link">Full ranking <ArrowRight size={14} /></Link>
          </div>
          {data.remediation.top_items.length === 0 ? (
            <div className="dashboard-empty">No remediation candidates found.</div>
          ) : (
            <div className="dashboard-list">
              {data.remediation.top_items.map((item, index) => (
                <Link to="/controls" className="dashboard-list-item" key={item.control_id}>
                  <span className="priority-number">{index + 1}</span>
                  <div className="list-item-main"><strong>{item.ref}</strong><span>{item.name}</span></div>
                  <div className="priority-score"><strong>{(item.priority_score ?? item.priority ?? 0).toFixed(1)}</strong><small>{item.requirement_leverage} reqs</small></div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      <section className="dashboard-section dashboard-panel">
        <div className="section-heading">
          <div><h3>Open coverage gaps</h3><p>Requirements that need a control or stronger mapping.</p></div>
          <Link to="/coverage" className="text-link">Review all gaps <ArrowRight size={14} /></Link>
        </div>
        {data.gaps.top_gaps.length === 0 ? (
          <div className="dashboard-empty"><CheckCircle2 size={18} /> No open gaps found.</div>
        ) : (
          <div className="gap-list">
            {data.gaps.top_gaps.map((gap) => (
              <div className="gap-list-item" key={`${gap.framework_key}-${gap.code}`}>
                <span className={`status-pill ${gap.status}`}>{formatStatus(gap.status)}</span>
                <strong>{gap.code}</strong>
                <span>{gap.title}</span>
                <span className="gap-framework">{gap.framework_key}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
