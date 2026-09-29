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

export function CenterPanel({ projectId, token, title, endpoints, actions = [] }: Props) {
  const [data, setData] = React.useState<any>(null);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [busy, setBusy] = React.useState(false);

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
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}
      {busy && !data && <p className="muted">Loading…</p>}
      {data && <pre className="extraction-json">{JSON.stringify(data, null, 2)}</pre>}
    </section>
  );
}
