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
  ready: "Ready",
  active: "Active",
  needs_setup: "Needs setup",
  empty: "Empty",
  degraded: "Degraded",
  error: "Error",
};

const icons: Record<string, string> = {
  ready: "●",
  active: "●",
  needs_setup: "●",
  empty: "○",
  degraded: "●",
  error: "●",
};

function moduleViewId(moduleId: string): string | null {
  const map: Record<string, string> = {
    design: "design-center",
    engineering: "design-center",
    commercial: "commercial",
    tender: "commercial",
    contract: "commercial",
    planning: "planning",
    procurement: "procurement",
    field: "field",
    quality: "quality",
    gis: "gis",
    prediction: "prediction",
    brain: "brain",
    integrations: "integrations",
    ops: "ops",
    cost: "cost-control",
    inventory: "inventory",
  };
  if (moduleId in map) return map[moduleId];
  if (["os-home", "assistant", "design-center", "commercial", "cost-control", "planning", "procurement", "inventory", "field", "quality", "gis", "prediction", "brain", "integrations", "ops"].includes(moduleId))
    return moduleId;
  return null;
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

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const snap = data?.data;
  const summary = data?.summary;
  const mods = snap?.modules || [];
  const active =
    summary?.module_counts?.active ??
    mods.filter((m: any) => m.status === "ready" || m.status === "active").length;
  const total = summary?.module_counts?.total ?? mods.length;
  const percent = total ? Math.round((active / total) * 100) : 0;
  const noDocs = documentCount === 0;

  return (
    <section className="panel os-home">
      <div className="os-hero">
        <div>
          <h1>Construction OS</h1>
          <p>Your project command center for delivery, cost, documents and field operations.</p>
        </div>
        <button type="button" className="button compact" disabled={busy} onClick={load}>
          {busy ? "Refreshing…" : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="error">
          {error}
          <details className="os-details">
            <summary>Technical details</summary>
            <span>Request failed while loading the OS snapshot.</span>
          </details>
        </div>
      )}

      {noDocs && (
        <div className="os-getting-started">
          <div>
            <h3>Get started with this project</h3>
            <p>
              No documents are indexed yet. Upload a BOQ, contract, drawing, or status report so the
              Assistant and Design center can work from real project evidence.
            </p>
          </div>
          <div className="os-getting-started-actions">
            <button type="button" className="button primary compact" onClick={() => onUploadRequest?.()}>
              Upload document
            </button>
            <button type="button" className="button compact" onClick={() => onNavigate?.("assistant")}>
              Open Assistant
            </button>
            <button type="button" className="button compact" onClick={() => onNavigate?.("design-center")}>
              Open Design
            </button>
          </div>
          <ol className="os-steps">
            <li>Upload PDF / DOCX / spreadsheet</li>
            <li>Wait until status is processed</li>
            <li>Ask the Assistant or generate BOQ in Design</li>
          </ol>
        </div>
      )}

      {busy && !snap ? (
        <p className="muted">Loading project readiness…</p>
      ) : snap ? (
        <>
          <div className="os-readiness">
            <div>
              <div className="os-readiness-top">
                <span>Project readiness</span>
                <span>
                  {active} of {total} modules active
                </span>
              </div>
              <div className="os-progress">
                <span style={{ width: percent + "%" }} />
              </div>
            </div>
            <div className="os-readiness-number">{percent}%</div>
          </div>

          {snap.recommended_actions?.length > 0 && (
            <div>
              <h3>Recommended actions</h3>
              <ul className="os-actions-list">
                {snap.recommended_actions.slice(0, 5).map((a: any, i: number) => {
                  const target = moduleViewId(String(a.module_id || a.module || a.view || ""));
                  return (
                    <li className="os-action-card" key={i}>
                      <span>→</span>
                      <div>
                        <b>{a.title}</b>
                        <span>{a.detail || a.description}</span>
                        {target && (
                          <button
                            type="button"
                            className="os-action"
                            onClick={() => onNavigate?.(target)}
                          >
                            Go →
                          </button>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          <h3>Modules</h3>
          <div className="os-grid">
            {mods.map((m: any) => {
              const target = moduleViewId(String(m.id || ""));
              return (
                <article className="os-module" key={m.id}>
                  <div className="os-module-head">
                    <h3>{m.label}</h3>
                    <span className={"os-badge " + (m.status || "empty")}>
                      {icons[m.status] || "•"} {labels[m.status] || m.status}
                    </span>
                  </div>
                  <p>
                    {m.status === "degraded"
                      ? "This module needs attention before it can be used reliably."
                      : m.status === "needs_setup"
                        ? "Complete the setup steps to activate this module."
                        : m.status === "empty"
                          ? "No data yet — generate or upload content for this module."
                          : m.message || "Module is ready for project work."}
                  </p>
                  <div className="os-actions">
                    <button
                      className="os-action"
                      type="button"
                      onClick={() => target && onNavigate?.(target)}
                      disabled={!target}
                    >
                      Open module →
                    </button>
                    {m.status === "degraded" && (
                      <details>
                        <summary className="os-action">Details</summary>
                        <div className="os-details">{m.message}</div>
                      </details>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
          {snap.notes && <p className="muted small">{snap.notes}</p>}
        </>
      ) : (
        !error && <p className="muted">No readiness data yet. Click Refresh after the API is awake.</p>
      )}
    </section>
  );
}
