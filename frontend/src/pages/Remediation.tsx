import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CircleAlert, ExternalLink, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { derivedApi } from "../api/derived";
import type { RemediationItem, RemediationRead } from "../types";

function RemediationLoading() {
  return (
    <div className="page-container remediation-page">
      <div className="page-header">
        <h2>Remediation Priority</h2>
        <p className="page-description">Ranked list of control improvements by risk and requirement leverage.</p>
      </div>
      <div className="dashboard-state" role="status"><div className="loading-spinner" /><p>Loading remediation ranking...</p></div>
    </div>
  );
}

function RiskLinks({ item }: { item: RemediationItem }) {
  if (item.risks.length === 0) return <span className="remediation-muted">No mapped risks</span>;
  return (
    <div className="remediation-link-list">
      {item.risks.map((risk) => (
        <Link to={`/risks/${risk.id ?? risk.risk_id}`} key={risk.id ?? risk.risk_id} className="remediation-risk-link">
          <span>{risk.ref}</span><small>{risk.title}</small><b>{risk.inherent_score}</b>
        </Link>
      ))}
    </div>
  );
}

function RequirementList({ item }: { item: RemediationItem }) {
  if (item.requirements.length === 0) return <span className="remediation-muted">No mapped requirements</span>;
  return (
    <div className="remediation-requirement-list">
      {item.requirements.map((requirement) => (
        <span key={requirement.id ?? requirement.requirement_id}><b>{requirement.code}</b>{requirement.title}<small>{requirement.framework_key}</small></span>
      ))}
    </div>
  );
}

function RemediationCard({ item, index }: { item: RemediationItem; index: number }) {
  return (
    <article className="remediation-card">
      <div className="remediation-card-rank">{index + 1}</div>
      <div className="remediation-card-main">
        <div className="remediation-card-header">
          <div>
            <div className="remediation-control-ref"><ShieldCheck size={15} /> {item.ref}</div>
            <h3>{item.name}</h3>
            <p>{item.category || "Uncategorized"} · <span className={`control-status-badge ${item.status}`}>{item.status.replaceAll("_", " ")}</span></p>
          </div>
          <div className="remediation-priority">
            <strong>{(item.priority_score ?? item.priority ?? 0).toFixed(1)}</strong>
            <span>priority score</span>
          </div>
        </div>
        <div className="remediation-leverage-grid">
          <div><strong>{item.risk_leverage}</strong><span>risks propped up</span></div>
          <div><strong>{(item.weighted_risk_leverage ?? item.weighted_leverage ?? 0).toFixed(1)}</strong><span>weighted risk leverage</span></div>
          <div><strong>{item.requirement_leverage}</strong><span>requirements satisfied</span></div>
        </div>
        <div className="remediation-card-details">
          <section><h4>Risks this would help</h4><RiskLinks item={item} /></section>
          <section><h4>Requirements this would satisfy</h4><RequirementList item={item} /></section>
        </div>
        <Link to="/controls" className="remediation-action">Open control library <ArrowRight size={14} /></Link>
      </div>
    </article>
  );
}

export function Remediation() {
  const [search, setSearch] = useState("");
  const query = useQuery<RemediationRead, Error>({
    queryKey: ["remediation"],
    queryFn: derivedApi.getRemediation,
    retry: false,
  });

  const items = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return query.data?.items ?? [];
    return (query.data?.items ?? []).filter((item) =>
      `${item.ref} ${item.name} ${item.category} ${item.risks.map((risk) => `${risk.ref} ${risk.title}`).join(" ")} ${item.requirements.map((requirement) => `${requirement.code} ${requirement.title}`).join(" ")}`
        .toLowerCase()
        .includes(term),
    );
  }, [query.data, search]);

  if (query.isLoading) return <RemediationLoading />;

  return (
    <div className="page-container remediation-page">
      <div className="page-header">
        <div>
          <h2>Remediation Priority</h2>
          <p className="page-description">Ranked list of control improvements by risk and requirement leverage.</p>
        </div>
      </div>

      {query.error || !query.data ? (
        <div className="dashboard-state dashboard-state-error" role="alert"><CircleAlert size={23} /><span>Remediation ranking unavailable. {query.error?.message || "No ranking data was returned."}</span></div>
      ) : (
        <>
          <section className="remediation-intro">
            <div className="remediation-intro-icon"><AlertTriangle size={22} /></div>
            <div>
              <h3>Fix the control propping up the most risk first.</h3>
              <p>Controls are ranked using the inherent risk they support and the number of requirements they satisfy. Higher priority means more impact from one remediation.</p>
            </div>
            <div className="remediation-weights">
              <span>Risk weight <b>{query.data.weights.W_RISK.toFixed(1)}</b></span>
              <span>Requirement weight <b>{query.data.weights.W_REQ.toFixed(1)}</b></span>
            </div>
          </section>
          <div className="remediation-toolbar">
            <label className="toolbar-search">
              <input aria-label="Search remediation items" placeholder="Search controls, risks, or requirements..." value={search} onChange={(event) => setSearch(event.target.value)} />
            </label>
            <span className="control-count">{items.length} of {query.data.candidate_count} candidates</span>
          </div>
          {query.data.items.length === 0 ? (
            <div className="dashboard-empty"><ShieldCheck size={23} /><p>No remediation candidates found. All controls are implemented or no controls have been added yet.</p><Link to="/controls" className="primary-btn">Open control library</Link></div>
          ) : items.length === 0 ? (
            <div className="dashboard-empty"><p>No remediation items match “{search}”.</p></div>
          ) : (
            <div className="remediation-list">{items.map((item, index) => <RemediationCard item={item} index={index} key={item.control_id} />)}</div>
          )}
          <div className="remediation-methodology"><ExternalLink size={14} /><span>Priority = weighted risk leverage × {query.data.weights.W_RISK.toFixed(1)} + requirement leverage × {query.data.weights.W_REQ.toFixed(1)}. Only partial and not-implemented controls are included.</span></div>
        </>
      )}
    </div>
  );
}
