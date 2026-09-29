import React from "react";
import { apiGet } from "../api";

type Props = { projectId: string; token: string };

export function OsHome({ projectId, token }: Props) {
  const [data, setData] = React.useState<any>(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function load() {
    if (!projectId || !token) return;
    setBusy(true); setError("");
    try {
      const j = await apiGet("/api/v1/projects/" + projectId + "/os/snapshot", token);
      setData(j);
    } catch (e: any) {
      setError(e.message || "Could not load Construction OS snapshot.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => { load(); }, [projectId, token]);

  const snap = data?.data;
  const summary = data?.summary;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Construction OS</h2>
        <button type="button" className="button compact" disabled={busy} onClick={load}>Refresh</button>
      </div>
      {error && <div className="error">{error}</div>}
      {busy && !snap && <p className="muted">Loading OS snapshot…</p>}
      {summary && (
        <div className="hint" style={{ marginBottom: 12 }}>
          <b>Readiness:</b> {summary.readiness || "—"}
          {" · "}
          <b>Active modules:</b> {summary.module_counts?.active ?? 0}/{summary.module_counts?.total ?? 0}
          {" · "}
          <b>Ops:</b> {summary.ops_health_status || "—"}
        </div>
      )}
      {snap?.recommended_actions?.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <h3>Recommended actions</h3>
          <ol>
            {snap.recommended_actions.map((a: any, i: number) => (
              <li key={i}>
                <b>{a.title}</b>
                <span className="muted"> — {a.detail}</span>
                <span className="muted"> [{a.module}]</span>
              </li>
            ))}
          </ol>
        </div>
      )}
      {snap?.modules && (
        <div>
          <h3>Modules</h3>
          {snap.modules.map((m: any) => (
            <div key={m.id} className="hint" style={{ marginBottom: 6 }}>
              <b>{m.label}</b>
              <span> · {m.status}</span>
              <span className="muted"> — {m.message}</span>
            </div>
          ))}
        </div>
      )}
      {snap?.notes && <p className="muted small">{snap.notes}</p>}
    </section>
  );
}
