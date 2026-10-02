import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };

type Item = {
  id: string;
  description: string;
  unit?: string | null;
  budget_quantity: number;
  budget_unit_rate: number;
  budget_amount: number;
  committed_amount: number;
  actual_amount: number;
  variance: number;
  progress_percent: number;
};

export function CostControlCenter({ projectId, token }: Props) {
  const [items, setItems] = React.useState<Item[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [overBudgetOnly, setOverBudgetOnly] = React.useState(false);

  async function load() {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    try {
      const r = await apiGet("/api/v1/projects/" + projectId + "/cost-control", token);
      setItems(r.data || []);
    } catch (e: any) {
      setError(e.message || "Could not load cost control.");
    } finally {
      setBusy(false);
      setLoading(false);
    }
  }

  async function sync() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await apiPost("/api/v1/projects/" + projectId + "/cost-control/sync", token, {});
      setItems(r.data || []);
      setNotice((r.count || 0) + " cost item(s) synchronized from approved estimate.");
    } catch (e: any) {
      setError(
        e.message ||
          "Could not sync. Approve estimate rates in Design, then try again."
      );
    } finally {
      setBusy(false);
      setLoading(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((x) => {
      const variance = Number(x.variance ?? Number(x.budget_amount || 0) - Number(x.actual_amount || 0));
      if (overBudgetOnly && variance >= 0) return false;
      if (!q) return true;
      return String(x.description || "")
        .toLowerCase()
        .includes(q);
    });
  }, [items, search, overBudgetOnly]);

  const budget = items.reduce((s, x) => s + Number(x.budget_amount || 0), 0);
  const committed = items.reduce((s, x) => s + Number(x.committed_amount || 0), 0);
  const actual = items.reduce((s, x) => s + Number(x.actual_amount || 0), 0);
  const variance = budget - actual;
  const progress = budget ? Math.min(100, (actual / budget) * 100) : 0;

  return (
    <section className="panel cost-control">
      <div className="panel-head">
        <div>
          <h2>Cost Control</h2>
          <p className="muted small">
            Budget vs commitment vs actual for general construction packages — driven by approved
            estimate and procurement delivery.
          </p>
        </div>
        <div className="row gap">
          <button type="button" className="button primary compact" onClick={sync} disabled={busy}>
            Sync from estimate
          </button>
          <button type="button" className="button compact" onClick={load} disabled={busy}>
            Refresh
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="cost-kpis">
        <div>
          <span>Budget</span>
          <b>{budget.toLocaleString()}</b>
        </div>
        <div>
          <span>Committed</span>
          <b>{committed.toLocaleString()}</b>
        </div>
        <div>
          <span>Actual</span>
          <b>{actual.toLocaleString()}</b>
        </div>
        <div>
          <span>Variance</span>
          <b style={{ color: variance < 0 ? "var(--error-ink)" : "var(--success-ink)" }}>
            {variance.toLocaleString()}
          </b>
        </div>
      </div>

      <div className="cost-progress">
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
          <span>Cost utilization</span>
          <b>{progress.toFixed(1)}%</b>
        </div>
        <div className="os-progress" style={{ marginTop: 8 }}>
          <span style={{ width: progress + "%", background: progress > 100 ? "#b42318" : undefined }} />
        </div>
      </div>

      {loading && !items.length ? (
        <p className="muted">Loading cost control…</p>
      ) : items.length === 0 ? (
        <div className="empty empty-card">
          <h3>No cost-control lines yet</h3>
          <p>
            Approve estimate rates in Design, then click <b>Sync from estimate</b>. Actuals update
            from delivered procurement quantities × approved rates.
          </p>
          <button type="button" className="button primary compact" disabled={busy} onClick={sync}>
            Sync from estimate
          </button>
        </div>
      ) : (
        <>
          <div className="boq-toolbar row gap">
            <input
              type="search"
              aria-label="Search cost items"
              placeholder="Search description…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: 220, flex: 1 }}
            />
            <label style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
              <input
                type="checkbox"
                checked={overBudgetOnly}
                onChange={(e) => setOverBudgetOnly(e.target.checked)}
              />
              <span style={{ fontSize: 12 }}>Over budget only</span>
            </label>
          </div>

          {filtered.length === 0 ? (
            <div className="empty empty-card">
              <h3>No matching cost lines</h3>
              <p>Try a different search or clear the over-budget filter.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Unit</th>
                    <th>Budget</th>
                    <th>Committed</th>
                    <th>Actual</th>
                    <th>Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((x) => {
                    const v = Number(
                      x.variance ?? Number(x.budget_amount || 0) - Number(x.actual_amount || 0)
                    );
                    return (
                      <tr key={x.id}>
                        <td>
                          <b>{x.description}</b>
                        </td>
                        <td>{x.unit || "—"}</td>
                        <td>{Number(x.budget_amount || 0).toLocaleString()}</td>
                        <td>{Number(x.committed_amount || 0).toLocaleString()}</td>
                        <td>{Number(x.actual_amount || 0).toLocaleString()}</td>
                        <td style={{ color: v < 0 ? "var(--error-ink)" : undefined, fontWeight: 650 }}>
                          {v.toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      <p className="muted small">
        Actual cost uses delivered procurement quantity × approved estimate rate. This is a project
        tracking basis, not certified accounting.
      </p>
    </section>
  );
}
