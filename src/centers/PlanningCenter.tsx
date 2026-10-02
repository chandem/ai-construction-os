import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };

type WbsNode = {
  id?: string;
  code?: string;
  name?: string;
  level?: number;
  work_section?: string;
  sort_order?: number;
};

type Activity = {
  id?: string;
  code?: string;
  name?: string;
  work_section?: string;
  status?: string;
  planned_start?: string;
  planned_finish?: string;
  duration_days?: number;
  percent_complete?: number | null;
};

export function PlanningCenter({ projectId, token }: Props) {
  const [summary, setSummary] = React.useState<any>(null);
  const [wbs, setWbs] = React.useState<WbsNode[]>([]);
  const [activities, setActivities] = React.useState<Activity[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [editId, setEditId] = React.useState<string | null>(null);
  const [editPct, setEditPct] = React.useState("");
  const [editNote, setEditNote] = React.useState("");

  async function load() {
    if (!projectId || !token) return;
    setLoading(true);
    setError("");
    try {
      const [sum, w, s] = await Promise.all([
        apiGet("/api/v1/projects/" + projectId + "/planning/summary", token),
        apiGet("/api/v1/projects/" + projectId + "/planning/wbs", token),
        apiGet("/api/v1/projects/" + projectId + "/planning/schedule", token),
      ]);
      setSummary(sum.data || sum);
      setWbs(w.data || sum.wbs_nodes || []);
      setActivities(s.data || sum.activities || []);
      if (w.warning || s.warning) {
        setNotice([w.warning, s.warning].filter(Boolean).join(" "));
      }
    } catch (e: any) {
      setError(e.message || "Could not load Planning Center.");
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  async function generate(path: string, label: string) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost("/api/v1/projects/" + projectId + path, token);
      setNotice(
        label +
          " completed: " +
          String(result.persisted ?? result.data?.length ?? 0) +
          " item(s)."
      );
      await load();
    } catch (e: any) {
      setError(e.message || label + " failed. Finish Design → BOQ → Estimate first.");
    } finally {
      setBusy(false);
    }
  }

  function startProgress(row: Activity) {
    if (!row.id) return;
    setEditId(row.id);
    setEditPct(row.percent_complete == null ? "0" : String(row.percent_complete));
    setEditNote("");
  }

  async function saveProgress(row: Activity) {
    if (!row.id) return;
    const pct = Number(editPct);
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      setError("Progress must be between 0 and 100.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const body = {
        activity_id: row.id,
        percent_complete: pct,
        note: editNote.trim() || null,
      };
      const result = await apiPost(
        "/api/v1/projects/" + projectId + "/field/progress",
        token,
        body
      );
      setNotice(result.warning || `Progress updated to ${pct}% for ${row.name || row.code}.`);
      setEditId(null);
      await load();
    } catch (e: any) {
      // Fallback to query params if body not accepted yet
      try {
        const qs = new URLSearchParams({
          activity_id: row.id,
          percent_complete: String(pct),
        });
        if (editNote.trim()) qs.set("note", editNote.trim());
        await apiPost(
          "/api/v1/projects/" + projectId + "/field/progress?" + qs.toString(),
          token
        );
        setNotice(`Progress updated to ${pct}%.`);
        setEditId(null);
        await load();
      } catch (err: any) {
        setError(err.message || e.message || "Could not update progress.");
      }
    } finally {
      setBusy(false);
    }
  }

  const overall =
    activities.length > 0
      ? Math.round(
          activities.reduce((s, a) => s + Number(a.percent_complete || 0), 0) / activities.length
        )
      : null;

  return (
    <section className="panel field-center">
      <div className="panel-head">
        <div>
          <h2>Planning Center</h2>
          <p className="muted small">
            WBS and schedule for general construction packages — generate from estimate, then track
            progress %.
          </p>
        </div>
        <div className="row gap">
          <button type="button" className="button compact" disabled={loading || busy} onClick={load}>
            Refresh
          </button>
          <button
            type="button"
            className="button primary compact"
            disabled={loading || busy}
            onClick={() => generate("/planning/wbs/generate", "WBS generation")}
          >
            Generate WBS
          </button>
          <button
            type="button"
            className="button primary compact"
            disabled={loading || busy}
            onClick={() => generate("/planning/schedule/generate", "Schedule generation")}
          >
            Generate schedule
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="center-summary">
        <div className="hint">
          <b>WBS nodes</b>
          <span> · {wbs.length}</span>
        </div>
        <div className="hint">
          <b>Activities</b>
          <span> · {activities.length}</span>
        </div>
        <div className="hint">
          <b>Avg progress</b>
          <span> · {overall == null ? "—" : overall + "%"}</span>
        </div>
        {summary?.section_count != null && (
          <div className="hint">
            <b>Sections</b>
            <span> · {summary.section_count}</span>
          </div>
        )}
      </div>

      {loading ? (
        <p className="muted">Loading planning data…</p>
      ) : (
        <>
          <h3>Work breakdown structure</h3>
          {wbs.length === 0 ? (
            <div className="empty empty-card">
              <h3>No WBS yet</h3>
              <p>
                Complete Design → BOQ → Estimate, then click <b>Generate WBS</b>. Works for building,
                civil, or mixed packages.
              </p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Level</th>
                    <th>Section</th>
                  </tr>
                </thead>
                <tbody>
                  {wbs.slice(0, 40).map((row, i) => (
                    <tr key={row.id || row.code || i}>
                      <td>
                        <code className="boq-code">{row.code || "—"}</code>
                      </td>
                      <td style={{ paddingLeft: 8 + (Number(row.level || 1) - 1) * 12 }}>
                        {row.name || "—"}
                      </td>
                      <td>{row.level ?? "—"}</td>
                      <td>{row.work_section || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3 style={{ marginTop: 24 }}>Schedule &amp; progress</h3>
          {activities.length === 0 ? (
            <div className="empty empty-card">
              <h3>No schedule activities</h3>
              <p>Generate schedule after WBS (or use Generate schedule to build both).</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Activity</th>
                    <th>Section</th>
                    <th>Start</th>
                    <th>Finish</th>
                    <th>%</th>
                    <th>Status</th>
                    <th>Update</th>
                  </tr>
                </thead>
                <tbody>
                  {activities.map((row, i) => (
                    <tr key={row.id || row.code || i}>
                      <td>
                        <code className="boq-code">{row.code || "—"}</code>
                      </td>
                      <td>{row.name || "—"}</td>
                      <td>{row.work_section || "—"}</td>
                      <td>{row.planned_start || "—"}</td>
                      <td>{row.planned_finish || "—"}</td>
                      <td>
                        {row.percent_complete == null ? "—" : Number(row.percent_complete) + "%"}
                      </td>
                      <td>
                        <span className={"status status-" + (row.status || "not_started")}>
                          {(row.status || "not_started").replace(/_/g, " ")}
                        </span>
                      </td>
                      <td>
                        {editId === row.id ? (
                          <div className="row gap">
                            <input
                              type="number"
                              min={0}
                              max={100}
                              step={1}
                              value={editPct}
                              onChange={(e) => setEditPct(e.target.value)}
                              style={{ width: 70 }}
                              aria-label="Percent complete"
                            />
                            <input
                              type="text"
                              value={editNote}
                              onChange={(e) => setEditNote(e.target.value)}
                              placeholder="Note"
                              style={{ width: 100 }}
                            />
                            <button
                              type="button"
                              className="button compact"
                              disabled={busy}
                              onClick={() => saveProgress(row)}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              className="button compact"
                              disabled={busy}
                              onClick={() => setEditId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="button compact"
                            disabled={busy || !row.id}
                            onClick={() => startProgress(row)}
                          >
                            Set %
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
