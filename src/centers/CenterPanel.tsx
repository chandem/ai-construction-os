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
  emptyHint?: string;
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

function friendlyError(message: string): string {
  const m = message.toLowerCase();
  if (m.includes("high demand") || m.includes("503") || m.includes("unavailable")) {
    return "AI service is busy (high demand). Wait a minute and try again.";
  }
  if (m.includes("failed to fetch") || m.includes("network")) {
    return "Network error — the API may be starting up. Retry in a few seconds.";
  }
  if (m.includes("cors")) {
    return "CORS blocked this request. Check Render CORS_ORIGINS includes your site URL.";
  }
  return message;
}

export function CenterPanel({
  projectId,
  token,
  title,
  endpoints,
  actions = [],
  emptyHint,
}: Props) {
  const [data, setData] = React.useState<Record<string, unknown> | null>(null);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [showRaw, setShowRaw] = React.useState(false);

  async function load() {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    setNotice("");
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
      setError(friendlyError(e.message || "Could not load " + title));
    } finally {
      setBusy(false);
    }
  }

  async function runAction(path: string, label: string) {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const p = path.replace("{id}", projectId);
      const [base, qs] = p.split("?");
      await apiPost(qs ? base + "?" + qs : base, token);
      setNotice(label + " completed.");
      await load();
    } catch (e: any) {
      setError(friendlyError(e.message || label + " failed."));
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const hasSqlHint =
    data &&
    Object.values(data).some(
      (v) =>
        v && typeof v === "object" && ("warning" in (v as object) || "error" in (v as object))
    );

  const allEmpty =
    data &&
    Object.values(data).every((v) => {
      if (!v || typeof v !== "object") return true;
      const o = v as Record<string, unknown>;
      if (Array.isArray(o.data) && o.data.length === 0) return true;
      if (Array.isArray(v) && (v as unknown[]).length === 0) return true;
      return false;
    });

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>{title}</h2>
        <div className="row gap">
          <button type="button" className="button compact" disabled={busy} onClick={load}>
            Refresh
          </button>
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              className="button primary compact"
              disabled={busy}
              onClick={() => runAction(a.path, a.label)}
            >
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
        <div className="empty empty-card">
          <h3>No data yet</h3>
          <p>
            {emptyHint ||
              "Open a project and click Refresh. If tables are missing, apply the matching file under supabase/."}
          </p>
        </div>
      )}
      {data && allEmpty && (
        <div className="empty empty-card">
          <h3>{title} is empty</h3>
          <p>
            {emptyHint ||
              "Use a Generate action above, or complete upstream steps (documents → Design → BOQ) first."}
          </p>
          {actions.length > 0 && (
            <p className="muted small">Tip: start with “{actions[0].label}”.</p>
          )}
        </div>
      )}
      {hasSqlHint && (
        <p className="muted small">
          Some endpoints returned a warning or error — often means the related SQL schema is not
          applied in Supabase yet.
        </p>
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
      {data && showRaw && <pre className="extraction-json">{JSON.stringify(data, null, 2)}</pre>}
    </section>
  );
}
