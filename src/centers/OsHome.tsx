import React from "react";
import { apiGet } from "../api";

type Props = {
  projectId: string;
  token: string;
  documentCount?: number;
  onNavigate?: (view: string) => void;
  onUploadRequest?: () => void;
};

const labels: Record<string, string> = {
  ready: "Ready", active: "Active", needs_setup: "Needs setup",
  empty: "No data yet", degraded: "Action required", error: "Error",
};

function moduleViewId(moduleId: string): string | null {
  const map: Record<string, string> = {
    design: "design-center", engineering: "design-center", commercial: "commercial",
    tender: "commercial", contract: "commercial", planning: "planning",
    procurement: "procurement", field: "field", quality: "quality", gis: "gis",
    prediction: "prediction", brain: "brain", integrations: "integrations",
    ops: "ops", cost: "cost-control", inventory: "inventory",
  };
  if (moduleId in map) return map[moduleId];
  return ["os-home", "assistant", "design-center", "commercial", "cost-control",
    "planning", "procurement", "inventory", "field", "quality", "gis",
    "prediction", "brain", "integrations", "ops"].includes(moduleId) ? moduleId : null;
}

export function OsHome({ projectId, token, documentCount = 0, onNavigate, onUploadRequest }: Props) {
  const [data, setData] = React.useState<any>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function load() {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    try {
      setData(await apiGet("/api/v1/projects/" + projectId + "/os/snapshot", token));
    } catch {
      setError("We couldn't load the project readiness summary. The API may be waking up — try Refresh.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => { load(); }, [projectId, token]);

  const snap = data?.data;
  const summary = data?.summary;
  const mods = snap?.modules || [];
  const active = summary?.module_counts?.active ??
    mods.filter((m: any) => m.status === "ready" || m.status === "active").length;
  const total = summary?.module_counts?.total ?? mods.length;
  const percent = total ? Math.round((active / total) * 100) : 0;
  const needsAttention = mods.filter((m: any) => ["degraded", "error", "needs_setup"].includes(m.status)).length;
  const actions = snap?.recommended_actions || [];

  return (
    <section className="panel os-home">
      <div className="dashboard-topline">
        <div className="dashboard-title">
          <p className="eyebrow">PROJECT OVERVIEW</p>
          <h1>Construction command center</h1>
          <p className="dashboard-subtitle">A live overview of project readiness, delivery modules, documents, and recommended next steps.</p>
        </div>
        <button type="button" className="button compact dashboard-refresh" disabled={busy || !projectId} onClick={load}>
          <span aria-hidden="true">↻</span> {busy ? "Refreshing…" : "Refresh data"}
        </button>
      </div>

      {error && <div className="error">{error}<details className="os-details"><summary>Technical details</summary><span>Request failed while loading the OS snapshot.</span></details></div>}

      <div className="dashboard-kpis">
        <article className="dashboard-kpi kpi-primary">
          <div className="kpi-label"><span className="kpi-icon">▦</span> Project readiness</div>
          <div className="kpi-value">{snap ? percent + "%" : "—"}</div>
          <div className="kpi-foot">{snap ? active + " of " + total + " modules active" : "Waiting for project data"}</div>
          <div className="kpi-progress"><span style={{ width: (snap ? percent : 0) + "%" }} /></div>
        </article>
        <article className="dashboard-kpi">
          <div className="kpi-label"><span className="kpi-icon">▤</span> Project documents</div>
          <div className="kpi-value">{documentCount}</div>
          <div className="kpi-foot">{documentCount ? "Documents uploaded to this project" : "Upload BOQ, drawings, or reports"}</div>
        </article>
        <article className="dashboard-kpi">
          <div className="kpi-label"><span className="kpi-icon">◈</span> Active modules</div>
          <div className="kpi-value">{snap ? active : "—"}<small>{snap ? " / " + total : ""}</small></div>
          <div className="kpi-foot">Tools currently marked ready or active</div>
        </article>
        <article className={"dashboard-kpi " + (needsAttention ? "kpi-warning" : "")}>
          <div className="kpi-label"><span className="kpi-icon">!</span> Needs attention</div>
          <div className="kpi-value">{snap ? needsAttention : "—"}</div>
          <div className="kpi-foot">{snap ? (needsAttention ? "Modules needing setup or review" : "No module alerts reported") : "Waiting for project data"}</div>
        </article>
      </div>

      {documentCount === 0 && (
        <div className="dashboard-start">
          <div className="dashboard-start-icon">↗</div>
          <div className="dashboard-start-copy">
            <span className="eyebrow">GET STARTED</span>
            <h3>Bring your project data into one place</h3>
            <p>Upload the records that define the works — BOQ, drawings, contracts, method statements, or progress reports.</p>
            <ol className="os-steps">
              <li>Upload project documents</li><li>Review processing results</li><li>Use AI to explore quantities, costs, and project information</li>
            </ol>
          </div>
          <div className="dashboard-start-actions">
            <button type="button" className="button primary compact" onClick={() => onUploadRequest?.()}>＋ Upload document</button>
            <button type="button" className="button compact" onClick={() => onNavigate?.("assistant")}>Ask AI assistant</button>
          </div>
        </div>
      )}

      {busy && !snap ? <div className="dashboard-loading"><span className="loading-dot" /> Loading live project summary…</div> : null}

      {snap && (
        <>
          <div className="dashboard-section-heading">
            <div><span className="eyebrow">OPERATIONS</span><h2>Project modules</h2><p>Open a work area or review modules that need attention.</p></div>
            <span className="dashboard-count">{mods.length} modules</span>
          </div>

          {actions.length > 0 && (
            <section className="dashboard-actions-panel">
              <div className="dashboard-panel-heading"><div><h3>Recommended next actions</h3><p>Suggested from the current project readiness snapshot.</p></div><span className="dashboard-count">{actions.length} suggested</span></div>
              <div className="dashboard-action-list">
                {actions.slice(0, 4).map((a: any, i: number) => {
                  const target = moduleViewId(String(a.module_id || a.module || a.view || ""));
                  return <article className="dashboard-action-row" key={i}>
                    <span className="action-number">{String(i + 1).padStart(2, "0")}</span>
                    <div className="dashboard-action-copy"><b>{a.title}</b><span>{a.detail || a.description || "Review this item to keep the project workspace up to date."}</span></div>
                    {target && <button type="button" className="os-action" onClick={() => onNavigate?.(target)}>Open →</button>}
                  </article>;
                })}
              </div>
            </section>
          )}

          <div className="dashboard-module-grid">
            {mods.map((m: any) => {
              const target = moduleViewId(String(m.id || ""));
              const moduleCopy = m.status === "degraded" || m.status === "error"
                ? "Review this module and resolve the reported issue."
                : m.status === "needs_setup"
                  ? "Complete setup to make this module ready."
                  : m.status === "empty"
                    ? "No data yet. Add project information to get started."
                    : m.message || "Ready for project work.";
              const statusClass = ["ready", "active"].includes(m.status) ? "good" :
                ["degraded", "error"].includes(m.status) ? "bad" :
                m.status === "needs_setup" ? "warning" : "neutral";
              return <article className="dashboard-module-card" key={m.id}>
                <div className="dashboard-module-top">
                  <span className="dashboard-module-symbol" aria-hidden="true">{String(m.label || "M").slice(0, 1).toUpperCase()}</span>
                  <span className={"dashboard-status " + statusClass}><i />{labels[m.status] || m.status || "Unknown"}</span>
                </div>
                <h3>{m.label}</h3>
                <p>{moduleCopy}</p>
                <div className="dashboard-module-footer">
                  {m.status === "degraded" || m.status === "error" ? <span className="dashboard-inline-alert">Review required</span> : <span className="dashboard-module-type">WORKSPACE MODULE</span>}
                  <button type="button" className="os-action" onClick={() => target && onNavigate?.(target)} disabled={!target}>Open module <span aria-hidden="true">→</span></button>
                </div>
                {(m.status === "degraded" || m.status === "error") && m.message && <details className="dashboard-module-details"><summary>Technical details</summary><p>{m.message}</p></details>}
              </article>;
            })}
          </div>
          {snap.notes && <p className="muted small">{snap.notes}</p>}
        </>
      )}

      {!busy && !snap && !error && <div className="dashboard-loading">No readiness data yet. Select a project and refresh to load its summary.</div>}
    </section>
  );
}
