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
  empty: "No data yet",
  degraded: "Action required",
  error: "Error",
};

const EMPTY_GUIDANCE: Record<string, { copy: string; action: string; view?: string; upload?: boolean }> = {
  design: {
    copy: "Upload drawings or specs, then open Design to review extracted elements.",
    action: "Upload drawings",
    upload: true,
  },
  engineering: {
    copy: "Upload drawings or BOQ documents to build the engineering baseline.",
    action: "Upload documents",
    upload: true,
  },
  commercial: {
    copy: "Add tender or contract data, or open Commercial after documents are processed.",
    action: "Open Commercial",
    view: "commercial",
  },
  tender: {
    copy: "Upload tender packages or generate packages from project documents.",
    action: "Open Commercial",
    view: "commercial",
  },
  contract: {
    copy: "Register contracts or upload agreement documents for review.",
    action: "Open Commercial",
    view: "commercial",
  },
  planning: {
    copy: "Create a WBS or schedule once scope and quantities are available.",
    action: "Open Planning",
    view: "planning",
  },
  procurement: {
    copy: "Add material needs from BOQ or open Procurement to start orders.",
    action: "Open Procurement",
    view: "procurement",
  },
  field: {
    copy: "Log site activities, materials, or equipment when work begins.",
    action: "Open Field",
    view: "field",
  },
  quality: {
    copy: "Record inspections and non-conformances as delivery progresses.",
    action: "Open Quality",
    view: "quality",
  },
  gis: {
    copy: "Add site locations or spatial layers when available.",
    action: "Open GIS",
    view: "gis",
  },
  prediction: {
    copy: "Run forecasts after schedule, cost, and risk data exist.",
    action: "Open Prediction",
    view: "prediction",
  },
  brain: {
    copy: "Ask the assistant once documents are uploaded and processed.",
    action: "Open Assistant",
    view: "assistant",
  },
  integrations: {
    copy: "Connect external systems when your workflow needs them. Optional for MVP use.",
    action: "Open Integrations",
    view: "integrations",
  },
  ops: {
    copy: "Ops fills as background jobs, health checks, and cost events run.",
    action: "Open Ops",
    view: "ops",
  },
  cost: {
    copy: "Add cost entries or generate estimates from BOQ lines.",
    action: "Open Cost Control",
    view: "cost-control",
  },
  inventory: {
    copy: "Track materials on site once procurement or field receipts start.",
    action: "Open Inventory",
    view: "inventory",
  },
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
  return [
    "os-home",
    "assistant",
    "design-center",
    "commercial",
    "cost-control",
    "planning",
    "procurement",
    "inventory",
    "field",
    "quality",
    "gis",
    "prediction",
    "brain",
    "integrations",
    "ops",
  ].includes(moduleId)
    ? moduleId
    : null;
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
  const needsAttention = mods.filter((m: any) =>
    ["degraded", "error", "needs_setup"].includes(m.status),
  ).length;
  const actions = snap?.recommended_actions || [];

  const checklist = [
    {
      id: "project",
      label: "Select or create a project",
      done: !!projectId,
      actionLabel: "Projects",
      onAction: undefined as (() => void) | undefined,
    },
    {
      id: "docs",
      label: "Upload BOQ, drawings, or reports",
      done: documentCount > 0,
      actionLabel: "Upload",
      onAction: () => onUploadRequest?.(),
    },
    {
      id: "review",
      label: "Review document processing results",
      done: documentCount > 0 && active > 0,
      actionLabel: "Design",
      onAction: () => onNavigate?.("design-center"),
    },
    {
      id: "ask",
      label: "Ask the AI assistant about the project",
      done: false,
      actionLabel: "Assistant",
      onAction: () => onNavigate?.("assistant"),
    },
  ];
  const checklistDone = checklist.filter((s) => s.done).length;
  const showChecklist = !!projectId && (documentCount === 0 || active === 0 || percent < 30);

  return (
    <section className="panel os-home">
      <div className="dashboard-topline">
        <div className="dashboard-title">
          <p className="eyebrow">PROJECT OVERVIEW</p>
          <h1>Construction command center</h1>
          <p className="dashboard-subtitle">
            A live overview of project readiness, delivery modules, documents, and recommended next steps.
          </p>
        </div>
        <button type="button" className="button compact dashboard-refresh" disabled={busy || !projectId} onClick={load}>
          <span aria-hidden="true">↻</span> {busy ? "Refreshing…" : "Refresh data"}
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

      <div className="dashboard-kpis">
        <article className="dashboard-kpi kpi-primary">
          <div className="kpi-label">
            <span className="kpi-icon">▦</span> Project readiness
          </div>
          <div className="kpi-value">{snap ? percent + "%" : "—"}</div>
          <div className="kpi-foot">
            {snap ? active + " of " + total + " modules active" : "Waiting for project data"}
          </div>
          <div className="kpi-progress">
            <span style={{ width: (snap ? percent : 0) + "%" }} />
          </div>
        </article>
        <article className="dashboard-kpi">
          <div className="kpi-label">
            <span className="kpi-icon">▤</span> Project documents
          </div>
          <div className="kpi-value">{documentCount}</div>
          <div className="kpi-foot">
            {documentCount ? "Documents uploaded to this project" : "Upload BOQ, drawings, or reports"}
          </div>
        </article>
        <article className="dashboard-kpi">
          <div className="kpi-label">
            <span className="kpi-icon">◈</span> Active modules
          </div>
          <div className="kpi-value">
            {snap ? active : "—"}
            <small>{snap ? " / " + total : ""}</small>
          </div>
          <div className="kpi-foot">Tools currently marked ready or active</div>
        </article>
        <article className={"dashboard-kpi " + (needsAttention ? "kpi-warning" : "")}>
          <div className="kpi-label">
            <span className="kpi-icon">!</span> Needs attention
          </div>
          <div className="kpi-value">{snap ? needsAttention : "—"}</div>
          <div className="kpi-foot">
            {snap
              ? needsAttention
                ? "Modules needing setup or review"
                : "No module alerts reported"
              : "Waiting for project data"}
          </div>
        </article>
      </div>

      {showChecklist && (
        <div className="dashboard-start">
          <div className="dashboard-start-icon">↗</div>
          <div className="dashboard-start-copy">
            <span className="eyebrow">GET STARTED</span>
            <h3>First-run checklist</h3>
            <p>
              {checklistDone} of {checklist.length} setup steps complete. Finish these to unlock modules beyond empty
              states.
            </p>
            <ol className="os-checklist">
              {checklist.map((step) => (
                <li key={step.id} className={step.done ? "done" : ""}>
                  <span className="os-check-mark" aria-hidden="true">
                    {step.done ? "✓" : "○"}
                  </span>
                  <span className="os-check-label">{step.label}</span>
                  {!step.done && step.onAction && (
                    <button type="button" className="os-check-action" onClick={step.onAction}>
                      {step.actionLabel}
                    </button>
                  )}
                </li>
              ))}
            </ol>
          </div>
          <div className="dashboard-start-actions">
            <button type="button" className="button primary compact" onClick={() => onUploadRequest?.()}>
              ＋ Upload document
            </button>
            <button type="button" className="button compact" onClick={() => onNavigate?.("assistant")}>
              Ask AI assistant
            </button>
          </div>
        </div>
      )}

      {busy && !snap ? (
        <div className="dashboard-loading">
          <span className="loading-dot" /> Loading live project summary…
        </div>
      ) : null}

      {snap && (
        <>
          <div className="dashboard-section-heading">
            <div>
              <span className="eyebrow">OPERATIONS</span>
              <h2>Project modules</h2>
              <p>Open a work area or follow the suggested next step on empty modules.</p>
            </div>
            <span className="dashboard-count">{mods.length} modules</span>
          </div>

          {actions.length > 0 && (
            <section className="dashboard-actions-panel">
              <div className="dashboard-panel-heading">
                <div>
                  <h3>Recommended next actions</h3>
                  <p>Suggested from the current project readiness snapshot.</p>
                </div>
                <span className="dashboard-count">{actions.length} suggested</span>
              </div>
              <div className="dashboard-action-list">
                {actions.map((a: any, i: number) => {
                  const target = moduleViewId(String(a.module_id || a.module || a.view || ""));
                  return (
                    <article className="dashboard-action-card" key={i}>
                      <div>
                        <b>{a.title || a.label || "Recommended action"}</b>
                        <span>{a.description || a.detail || a.reason || ""}</span>
                      </div>
                      {target && (
                        <button type="button" className="os-action" onClick={() => onNavigate?.(target)}>
                          Open →
                        </button>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>
          )}

          <div className="dashboard-module-grid">
            {mods.map((m: any) => {
              const id = String(m.id || "");
              const target = moduleViewId(id);
              const guide = EMPTY_GUIDANCE[id];
              const isEmpty = m.status === "empty" || m.status === "needs_setup";
              const moduleCopy =
                m.status === "degraded" || m.status === "error"
                  ? "Review this module and resolve the reported issue."
                  : isEmpty && guide
                    ? guide.copy
                    : m.status === "needs_setup"
                      ? "Complete setup to make this module ready."
                      : m.status === "empty"
                        ? "No data yet — upload documents or generate data to unlock this module."
                        : m.message || "Ready for project work.";
              const statusClass = ["ready", "active"].includes(m.status)
                ? "good"
                : ["degraded", "error"].includes(m.status)
                  ? "bad"
                  : m.status === "needs_setup"
                    ? "warning"
                    : "neutral";
              const primaryLabel =
                isEmpty && guide
                  ? guide.action
                  : m.status === "degraded" || m.status === "error"
                    ? "Review module"
                    : "Open module";
              const onPrimary = () => {
                if (isEmpty && guide?.upload) {
                  onUploadRequest?.();
                  return;
                }
                const dest = (isEmpty && guide?.view) || target;
                if (dest) onNavigate?.(dest);
              };

              return (
                <article className="dashboard-module-card" key={m.id}>
                  <div className="dashboard-module-top">
                    <span className="dashboard-module-symbol" aria-hidden="true">
                      {String(m.label || "M").slice(0, 1).toUpperCase()}
                    </span>
                    <span className={"dashboard-status " + statusClass}>
                      <i />
                      {labels[m.status] || m.status || "Unknown"}
                    </span>
                  </div>
                  <h3>{m.label}</h3>
                  <p>{moduleCopy}</p>
                  <div className="dashboard-module-footer">
                    {m.status === "degraded" || m.status === "error" ? (
                      <span className="dashboard-inline-alert">Review required</span>
                    ) : (
                      <span className="dashboard-module-type">WORKSPACE MODULE</span>
                    )}
                    <button
                      type="button"
                      className="os-action"
                      onClick={onPrimary}
                      disabled={!guide?.upload && !target && !(isEmpty && guide?.view)}
                    >
                      {primaryLabel} <span aria-hidden="true">→</span>
                    </button>
                  </div>
                  {(m.status === "degraded" || m.status === "error") && m.message && (
                    <details className="dashboard-module-details">
                      <summary>Technical details</summary>
                      <p>{m.message}</p>
                    </details>
                  )}
                </article>
              );
            })}
          </div>
          {snap.notes && <p className="muted small">{snap.notes}</p>}
        </>
      )}

      {!busy && !snap && !error && (
        <div className="dashboard-loading">
          No readiness data yet. Select a project and refresh to load its summary.
        </div>
      )}
    </section>
  );
}
