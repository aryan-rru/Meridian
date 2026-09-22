import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, CheckCircle2, CircleAlert, FileText, Link2, ShieldCheck } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { risksApi } from "../api/risks";
import type { TraceabilityControl, TraceabilityRead } from "../types";

function RiskDetailLoading({ id }: { id: string }) {
  return (
    <div className="page-container risk-detail-page">
      <div className="page-header">
        <Link to="/risks" className="back-link"><ArrowLeft size={16} /> Back to Risk Register</Link>
        <h2>Risk Traceability: {id}</h2>
        <p className="page-description">Risk → Controls → Requirements → Frameworks</p>
      </div>
      <div className="dashboard-state" role="status">
        <div className="loading-spinner" />
        <p>Loading risk traceability...</p>
      </div>
    </div>
  );
}

function BandSummary({ label, score, band }: { label: string; score: number; band: { name: string; color: string } }) {
  return (
    <div className="risk-detail-score">
      <span className="detail-label">{label}</span>
      <strong>{score}</strong>
      <span className="risk-band-chip" style={{ borderColor: band.color, color: band.color }}>
        <i style={{ backgroundColor: band.color }} /> {band.name}
      </span>
    </div>
  );
}

function ControlTrace({ control }: { control: TraceabilityControl }) {
  const grouped = control.requirements.reduce<Record<string, typeof control.requirements>>((groups, requirement) => {
    const key = requirement.framework.framework_key;
    (groups[key] ??= []).push(requirement);
    return groups;
  }, {});

  return (
    <article className="trace-control">
      <div className="trace-control-header">
        <div className="trace-control-title">
          <ShieldCheck size={19} />
          <div>
            <strong>{control.ref} · {control.name}</strong>
            <span>{control.category} · Owner: {control.owner || "Unassigned"}</span>
          </div>
        </div>
        <span className={`control-status-badge ${control.status}`}>{control.status.replaceAll("_", " ")}</span>
      </div>
      <div className="trace-control-meta">
        <span><Link2 size={14} /> {control.requirements_satisfied_count} requirements satisfied</span>
        <Link to="/evidence" className="trace-evidence-link"><FileText size={14} /> {control.evidence_count} linked evidence</Link>
      </div>
      {control.requirements.length === 0 ? (
        <p className="detail-muted trace-empty">No requirements are mapped to this control.</p>
      ) : (
        <div className="trace-requirements">
          {Object.entries(grouped).map(([frameworkKey, requirements]) => {
            const framework = requirements[0].framework;
            return (
              <section className="trace-framework" key={frameworkKey}>
                <h4><i style={{ backgroundColor: framework.color }} />{framework.framework_name}</h4>
                <div className="trace-requirement-list">
                  {requirements.map((requirement) => (
                    <div className="trace-requirement" key={requirement.requirement_id}>
                      <strong>{requirement.code}</strong>
                      <span>{requirement.title}</span>
                      <small>{requirement.category} · {requirement.coverage_level} coverage</small>
                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </article>
  );
}

function AssurancePanel({ data }: { data: TraceabilityRead }) {
  const flagged = data.assurance.flag === "unsupported_residual";
  return (
    <section className={`trace-assurance ${flagged ? "flagged" : "sound"}`} aria-labelledby="assurance-heading">
      <div className="trace-assurance-icon">
        {flagged ? <AlertTriangle size={22} /> : <CheckCircle2 size={22} />}
      </div>
      <div>
        <h3 id="assurance-heading">{flagged ? "Unearned residual risk" : "Residual risk assurance"}</h3>
        <p>{data.assurance.message || (flagged
          ? "The residual score is lower than the inherent score, but supporting controls have not earned that reduction."
          : "The residual score is supported by the mapped control statuses.")}</p>
        <div className="trace-assurance-stats">
          <span>{data.assurance.supporting_count} supporting controls</span>
          <span>{data.assurance.implemented_count} implemented</span>
          <span>{data.assurance.partial_count} partial</span>
          <span>Weakest: {data.assurance.weakest_status?.replaceAll("_", " ") || "none"}</span>
        </div>
      </div>
    </section>
  );
}

export function RiskDetail() {
  const { id = "" } = useParams<{ id: string }>();
  const query = useQuery<TraceabilityRead, Error>({
    queryKey: ["risk-traceability", id],
    queryFn: () => risksApi.getTraceability(id),
    enabled: Boolean(id),
    retry: false,
  });

  if (query.isLoading) return <RiskDetailLoading id={id} />;

  if (query.error || !query.data) {
    return (
      <div className="page-container risk-detail-page">
        <div className="page-header">
          <Link to="/risks" className="back-link"><ArrowLeft size={16} /> Back to Risk Register</Link>
          <h2>Risk Traceability: {id}</h2>
          <p className="page-description">Risk → Controls → Requirements → Frameworks</p>
        </div>
        <div className="dashboard-state dashboard-state-error" role="alert">
          <CircleAlert size={23} />
          <span>Risk traceability unavailable. {query.error?.message || "No risk data was returned."}</span>
        </div>
      </div>
    );
  }

  const data = query.data;
  return (
    <div className="page-container risk-detail-page">
      <div className="page-header">
        <Link to="/risks" className="back-link"><ArrowLeft size={16} /> Back to Risk Register</Link>
        <h2>Risk Traceability: {data.risk.ref}</h2>
        <p className="page-description">Risk → Controls → Requirements → Frameworks</p>
      </div>

      <section className="risk-detail-summary">
        <div className="risk-detail-summary-main">
          <div className="risk-detail-kicker">{data.risk.ref} · {data.risk.category}</div>
          <h3>{data.risk.title}</h3>
          <p>{data.risk.description || "No description provided."}</p>
          <div className="risk-detail-fields">
            <span><b>Owner</b>{data.risk.owner || "Unassigned"}</span>
            <span><b>Status</b>{data.risk.status.replaceAll("_", " ")}</span>
            <span><b>Treatment</b>{data.risk.treatment.replaceAll("_", " ")}</span>
          </div>
        </div>
        <div className="risk-detail-scores">
          <BandSummary label="Inherent" score={data.risk.inherent_score} band={data.risk.inherent_band} />
          <BandSummary label="Residual" score={data.risk.residual_score} band={data.risk.residual_band} />
        </div>
      </section>

      <AssurancePanel data={data} />

      <section className="trace-summary-grid" aria-label="Traceability summary">
        <div><strong>{data.aggregate.control_count}</strong><span>Supporting controls</span></div>
        <div><strong>{data.aggregate.distinct_requirement_count}</strong><span>Requirements satisfied</span></div>
        <div><strong>{data.aggregate.frameworks_touched}</strong><span>Frameworks touched</span></div>
        <div><strong>{data.aggregate.total_evidence_count}</strong><span>Linked evidence</span></div>
      </section>

      <section className="trace-framework-summary" aria-labelledby="framework-summary-heading">
        <div className="section-heading">
          <div><h3 id="framework-summary-heading">Frameworks in scope</h3><p>Requirements reached through this risk's controls.</p></div>
        </div>
        {data.aggregate.frameworks.length === 0 ? (
          <p className="detail-muted">No framework requirements are currently reached.</p>
        ) : (
          <div className="trace-framework-chips">
            {data.aggregate.frameworks.map((framework) => (
              <span key={framework.framework_key}><i style={{ backgroundColor: framework.color }} />{framework.framework_name} · {framework.requirement_count} requirements</span>
            ))}
          </div>
        )}
      </section>

      <section className="trace-tree" aria-labelledby="trace-tree-heading">
        <div className="section-heading">
          <div><h3 id="trace-tree-heading">Traceability tree</h3><p>Controls supporting this risk and the requirements they satisfy.</p></div>
        </div>
        {data.controls.length === 0 ? (
          <div className="dashboard-empty"><AlertTriangle size={22} /><p>No mitigating controls are linked to this risk yet.</p><Link to="/controls" className="primary-btn">Open control library</Link></div>
        ) : (
          <div className="trace-control-list">{data.controls.map((control) => <ControlTrace key={control.control_id} control={control} />)}</div>
        )}
      </section>
    </div>
  );
}
