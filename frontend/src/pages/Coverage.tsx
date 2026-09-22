import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Check, CircleAlert, Info, Search, X } from "lucide-react";
import { Link } from "react-router-dom";
import { derivedApi } from "../api/derived";
import type { CoverageRead, GapItem, GapsRead, FrameworkCoverage } from "../types";

type CoverageStatus = "covered" | "partial" | "gap";

function CoverageLoading() {
  return (
    <div className="page-container coverage-page">
      <div className="page-header">
        <h2>Coverage Heatmap</h2>
        <p className="page-description">Loading framework and requirement coverage...</p>
      </div>
      <div className="dashboard-state" role="status">
        <div className="loading-spinner" />
        <p>Loading coverage data...</p>
      </div>
    </div>
  );
}

function CoverageError({ message }: { message: string }) {
  return (
    <div className="dashboard-state dashboard-state-error" role="alert">
      <CircleAlert size={23} />
      <span>Coverage unavailable. {message}</span>
    </div>
  );
}

function CoverageLegend() {
  return (
    <div className="coverage-legend" aria-label="Coverage legend">
      <span><i className="coverage-key covered"><Check size={12} /></i> Covered</span>
      <span><i className="coverage-key partial"><Info size={12} /></i> Partial</span>
      <span><i className="coverage-key gap"><X size={12} /></i> Gap</span>
    </div>
  );
}

function CategoryHeatmap({
  framework,
  gapByRequirement,
  onSelectGap,
}: {
  framework: FrameworkCoverage;
  gapByRequirement: Map<string, GapItem>;
  onSelectGap: (gap: GapItem) => void;
}) {
  return (
    <section className="coverage-framework-panel" aria-labelledby={`framework-${framework.framework_key}`}>
      <div className="coverage-framework-header">
        <div className="coverage-framework-title">
          <span className="framework-color-dot" style={{ backgroundColor: framework.framework_color }} />
          <div>
            <h3 id={`framework-${framework.framework_key}`}>{framework.framework_name}</h3>
            <p>{framework.covered} covered of {framework.total} requirements</p>
          </div>
        </div>
        <strong>{framework.coverage_percent}%</strong>
      </div>
      <div className="coverage-progress large">
        <span style={{ width: `${framework.coverage_percent}%`, backgroundColor: framework.framework_color }} />
      </div>
      <div className="coverage-framework-stats">
        <span className="covered-text">{framework.covered} covered</span>
        <span className="partial-text">{framework.partial} partial</span>
        <span className="gap-text">{framework.gap} gaps</span>
      </div>
      <div className="coverage-category-grid">
        {framework.categories.map((category) => (
          <div className="coverage-category" key={category.category}>
            <div className="coverage-category-header">
              <strong>{category.category || "Uncategorized"}</strong>
              <span>{category.coverage_percent}%</span>
            </div>
            <div className="coverage-cells" aria-label={`${category.category} coverage`}>
              {Array.from({ length: category.total }).map((_, index) => {
                const status: CoverageStatus =
                  index < category.covered
                    ? "covered"
                    : index < category.covered + category.partial
                      ? "partial"
                      : "gap";
                const gap = status !== "covered"
                  ? [...gapByRequirement.values()].find(
                      (item) =>
                        item.framework_key === framework.framework_key &&
                        item.category === category.category &&
                        item.status === status,
                    )
                  : undefined;
                return (
                  <button
                    type="button"
                    className={`coverage-cell ${status}`}
                    key={`${category.category}-${index}`}
                    aria-label={`${category.category} ${status}${gap ? `: ${gap.code}` : ""}`}
                    title={gap ? `${gap.code}: ${gap.title}` : `${category.category}: ${status}`}
                    onClick={() => gap && onSelectGap(gap)}
                    disabled={!gap}
                  >
                    {status === "covered" ? <Check size={12} /> : status === "partial" ? <Info size={12} /> : <X size={12} />}
                  </button>
                );
              })}
            </div>
            <div className="coverage-category-meta">
              {category.covered} covered · {category.partial} partial · {category.gap} gaps
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function GapDetail({ gap, onClose }: { gap: GapItem; onClose: () => void }) {
  return (
    <aside className="gap-detail-panel" role="dialog" aria-modal="true" aria-label={`Gap detail for ${gap.code}`}>
      <div className="gap-detail-header">
        <div>
          <span className={`status-pill ${gap.status}`}>{gap.status}</span>
          <h3>{gap.code}</h3>
          <p>{gap.title}</p>
        </div>
        <button type="button" className="icon-btn" onClick={onClose} aria-label="Close gap detail"><X size={18} /></button>
      </div>
      <div className="gap-detail-section">
        <span className="detail-label">Framework and category</span>
        <strong>{gap.framework_name}</strong>
        <span>{gap.category || "Uncategorized"}</span>
      </div>
      <div className="gap-detail-section">
        <span className="detail-label">How to resolve it</span>
        <p>{gap.resolution_hint}</p>
      </div>
      <div className="gap-detail-section">
        <span className="detail-label">Mapped controls</span>
        {gap.mapped_controls.length === 0 ? (
          <p className="detail-muted">No control is currently mapped to this requirement.</p>
        ) : (
          <div className="mapped-control-list">
            {gap.mapped_controls.map((control) => (
              <Link to="/controls" className="mapped-control" key={control.id}>
                <strong>{control.ref}</strong>
                <span>{control.name}</span>
                <small>{control.status} · {control.coverage_level} coverage</small>
              </Link>
            ))}
          </div>
        )}
      </div>
      <Link to="/controls" className="primary-btn gap-detail-action">Open control library</Link>
    </aside>
  );
}

export function Coverage() {
  const [search, setSearch] = useState("");
  const [selectedGap, setSelectedGap] = useState<GapItem | null>(null);
  const coverageQuery = useQuery<CoverageRead, Error>({
    queryKey: ["coverage"],
    queryFn: derivedApi.getCoverage,
    retry: false,
  });
  const gapsQuery = useQuery<GapsRead, Error>({
    queryKey: ["coverage", "gaps"],
    queryFn: derivedApi.getGaps,
    retry: false,
  });

  const gapByRequirement = useMemo(
    () => new Map((gapsQuery.data?.items ?? []).map((gap) => [gap.requirement_id, gap])),
    [gapsQuery.data],
  );
  const frameworks = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!coverageQuery.data || !query) return coverageQuery.data?.frameworks ?? [];
    return coverageQuery.data.frameworks.filter((framework) =>
      `${framework.framework_name} ${framework.framework_key}`.toLowerCase().includes(query),
    );
  }, [coverageQuery.data, search]);

  if (coverageQuery.isLoading || gapsQuery.isLoading) return <CoverageLoading />;
  if (coverageQuery.error || gapsQuery.error) {
    return <CoverageError message={coverageQuery.error?.message || gapsQuery.error?.message || "The API request failed."} />;
  }
  if (!coverageQuery.data || !gapsQuery.data) return <CoverageError message="No coverage data was returned." />;

  return (
    <div className="page-container coverage-page">
      <div className="page-header">
        <h2>Coverage Heatmap</h2>
        <p className="page-description">
          Find the requirements an audit would ask about but your controls do not fully answer.
        </p>
      </div>

      <div className="coverage-summary">
        <div><strong>{coverageQuery.data.totals.coverage_percent}%</strong><span>Overall coverage</span></div>
        <div><strong>{coverageQuery.data.totals.covered}</strong><span>Covered</span></div>
        <div><strong>{coverageQuery.data.totals.partial}</strong><span>Partial</span></div>
        <div><strong className="gap-text">{coverageQuery.data.totals.gap}</strong><span>Gaps</span></div>
      </div>

      <div className="coverage-toolbar">
        <label className="coverage-search"><Search size={16} /><input aria-label="Search frameworks" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search frameworks..." /></label>
        <CoverageLegend />
        <button type="button" className="gap-count-button" onClick={() => setSelectedGap(gapsQuery.data.items[0] ?? null)} disabled={!gapsQuery.data.items.length}>
          <AlertTriangle size={15} /> {gapsQuery.data.gap_count} open gaps
        </button>
      </div>

      {frameworks.length === 0 ? (
        <div className="empty-panel"><Search size={22} /><strong>No frameworks match your search.</strong></div>
      ) : (
        <div className="coverage-framework-list">
          {frameworks.map((framework) => (
            <CategoryHeatmap key={framework.framework_key} framework={framework} gapByRequirement={gapByRequirement} onSelectGap={setSelectedGap} />
          ))}
        </div>
      )}

      {selectedGap && <div className="gap-detail-backdrop" onClick={(event) => event.target === event.currentTarget && setSelectedGap(null)}><GapDetail gap={selectedGap} onClose={() => setSelectedGap(null)} /></div>}
    </div>
  );
}
