import React from "react";
import { apiGet, apiPost } from "../api";

type Endpoint = { key: string; path: string };
type Action = { path: string; label: string };

type Props = {
  projectId: string;
  token: string;
  title: string;
  endpoints: Endpoint[];
  actions?: Action[];
};

function summarizeValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "object" && value !== null && "error" in (value as object)) {
    return "error";
  }
  if (Array.isArray(value)) return `${value.length} items`;
  if (typeof value === "object") {
    const o = value as Record<string, unknown>;
    if (Array.isArray(o.data)) return `${o.data.length} rows`;
    if (o.data && typeof o.data === "object" && !Array.isArray(o.data)) return "object";
    if (typeof o.warning === "string") return "needs SQL";
    const keys = Object.keys(o);
    return `${keys.length} keys`;
  }
  return String(value);
}

export function CenterPanel({ projectId, token, title, endpoints, actions = [] }: Props) {
  const [data, setData] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [showRaw, setShowRaw] = React.useState(false);

  async function load() {
    if (!projectId || !token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const results: Record<string, unknown> = {};
      for (const ep of endpoints) {
        try {
          results[ep.key] = await apiGet(ep.path.replace("{id}", projectId), token);
        } catch (e: any) {
          results[ep.key] = { error: e.message };
        }
      }
      setData(results);
      setNotice(title + " loaded.");
    } catch (e: any) {
      setError(e.message || "Could not load " + title);
    } finally {
      setBusy(false);
    }
  }

  async function runAction(path: string, label: string) {
    if (!projectId || !token) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const p = path.replace("{id}", projectId);
      const [base, qs] = p.split("?");
      await apiPost(qs ? base + "?" + qs : base, token);
      setNotice(label + " completed.");
      await load();
    } catch (e: any) {
      setError(e.message || label + " failed.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => { load(); }, [projectId, token]);

  const hasSqlHint = data && Object.values(data).some(
    (v) => v && typeof v === "object" && ("warning" in (v as object) || "error" in (v as object))
  );

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <div className="row gap">
          <button type="button" className="button compact" disabled={busy} onClick={load}>Refresh</button>
          {actions.map((a) => (
            <button key={a.label} type="button" className="button primary compact" disabled={busy} onClick={() => runAction(a.path, a.label)}>
              {a.label}
            </button>
          ))}
          {data && (
            <button type="button" className="button compact" onClick={() => setShowRaw((v) => !v)}>
              {showRaw ? "Hide raw" : "Show raw"}
            </button>
          )}
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}
      {busy && !data && <p className="muted">Loading…</p>}
      {!busy && !data && !error && (
        <div className="empty">
          <p>No data yet. Open a project and click Refresh. If tables are missing, apply the matching file under <code>supabase/</code>.</p>
        </div>
      )}
      {hasSqlHint && (
        <p className="muted small">Some endpoints returned a warning or error — often means the related SQL schema is not applied in Supabase yet.</p>
      )}
      {data && (
        <div className="center-summary">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="hint" style={{ marginBottom: 8 }}>
              <b>{key}</b>
              <span> · {summarizeValue(value)}</span>
            </div>
          ))}
        </div>
      )}
      {data && showRaw && (
        <pre className="extraction-json">{JSON.stringify(data, null, 2)}</pre>
      )}
    </section>
  );
}
