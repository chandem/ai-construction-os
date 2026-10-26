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
  predecessor_ids?: string[] | null;
};

function analyzeCriticalPath(activities: Activity[]) {
  const rows = activities.filter((a) => Boolean(a.id));
  const byId = new Map(rows.map((a) => [a.id as string, a]));
  const predecessors = new Map<string, string[]>();
  const successors = new Map<string, string[]>();
  rows.forEach((a) => {
    const id = a.id as string;
    const valid = (a.predecessor_ids || []).filter((p) => p !== id && byId.has(p));
    predecessors.set(id, valid);
    successors.set(id, []);
  });
  predecessors.forEach((preds, id) => preds.forEach((p) => successors.get(p)?.push(id)));
  const indegree = new Map(rows.map((a) => [a.id as string, (predecessors.get(a.id as string) || []).length]));
  const queue = rows.filter((a) => indegree.get(a.id as string) === 0).map((a) => a.id as string);
  const order: string[] = [];
  while (queue.length) {
    const id = queue.shift()!;
    order.push(id);
    (successors.get(id) || []).forEach((next) => {
      indegree.set(next, (indegree.get(next) || 0) - 1);
      if (indegree.get(next) === 0) queue.push(next);
    });
  }
  if (order.length !== rows.length || !rows.length) return { criticalIds: new Set<string>(), duration: 0, hasCycle: order.length !== rows.length };
  const durationOf = (id: string) => Math.max(1, Number(byId.get(id)?.duration_days || 1));
  const earlyStart = new Map<string, number>();
  const earlyFinish = new Map<string, number>();
  order.forEach((id) => {
    const start = Math.max(0, ...(predecessors.get(id) || []).map((p) => earlyFinish.get(p) || 0));
    earlyStart.set(id, start);
    earlyFinish.set(id, start + durationOf(id));
  });
  const projectDuration = Math.max(0, ...earlyFinish.values());
  const lateFinish = new Map<string, number>();
  const lateStart = new Map<string, number>();
  [...order].reverse().forEach((id) => {
    const next = successors.get(id) || [];
    const finish = next.length ? Math.min(...next.map((n) => lateStart.get(n) ?? projectDuration)) : projectDuration;
    lateFinish.set(id, finish);
    lateStart.set(id, finish - durationOf(id));
  });
  const criticalIds = new Set<string>();
  order.forEach((id) => {
    if (Math.abs((lateStart.get(id) || 0) - (earlyStart.get(id) || 0)) < 0.0001) criticalIds.add(id);
  });
  return { criticalIds, duration: projectDuration, hasCycle: false };
}

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
  const [activitySearch, setActivitySearch] = React.useState("");
  const [activityFilter, setActivityFilter] = React.useState("all");
  const [dependencyEditId, setDependencyEditId] = React.useState<string | null>(null);
  const [selectedPredecessors, setSelectedPredecessors] = React.useState<string[]>([]);

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

  function startDependencies(row: Activity) {
    if (!row.id) return;
    setDependencyEditId(row.id);
    setSelectedPredecessors((row.predecessor_ids || []).filter((id) => id !== row.id));
    setError("");
    setNotice("");
  }

  async function saveDependencies(row: Activity) {
    if (!row.id) return;
    if (selectedPredecessors.includes(row.id)) {
      setError("An activity cannot depend on itself.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost(
        "/api/v1/projects/" + projectId + "/planning/schedule/" + row.id + "/dependencies",
        token,
        { predecessor_ids: selectedPredecessors }
      );
      setNotice(result.warning || "Dependencies saved.");
      setDependencyEditId(null);
      await load();
    } catch (e: any) {
      setError(e.message || "Could not save activity dependencies.");
    } finally {
      setBusy(false);
    }
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

  const filteredActivities = activities.filter((activity) => {
    const query = activitySearch.trim().toLowerCase();
    const matchesQuery = !query || [activity.name, activity.code, activity.work_section, activity.status]
      .some((value) => String(value || "").toLowerCase().includes(query));
    const status = String(activity.status || "not_started").toLowerCase();
    const matchesStatus = activityFilter === "all" ||
      (activityFilter === "overdue" ? Boolean(activity.planned_finish && activity.planned_finish < new Date().toISOString().slice(0, 10) && Number(activity.percent_complete || 0) < 100) :
       activityFilter === "in_progress" ? status === "in_progress" || (Number(activity.percent_complete || 0) > 0 && Number(activity.percent_complete || 0) < 100) :
       activityFilter === "completed" ? status === "completed" || Number(activity.percent_complete || 0) >= 100 :
       activityFilter === "not_started" ? status === "not_started" || Number(activity.percent_complete || 0) === 0 : true);
    return matchesQuery && matchesStatus;
  });
  const datedActivities = filteredActivities.filter((a) => a.planned_start && a.planned_finish && !Number.isNaN(Date.parse(a.planned_start)) && !Number.isNaN(Date.parse(a.planned_finish)));
  const criticalPath = analyzeCriticalPath(activities);
  const timelineStart = datedActivities.length ? Math.min(...datedActivities.map((a) => Date.parse(a.planned_start!))) : 0;
  const timelineEnd = datedActivities.length ? Math.max(...datedActivities.map((a) => Date.parse(a.planned_finish!))) : 0;
  const timelineDays = datedActivities.length ? Math.max(1, Math.round((timelineEnd - timelineStart) / 86400000) + 1) : 0;
  const dateLabel = (value?: string) => value && !Number.isNaN(Date.parse(value)) ? new Date(value + (value.length === 10 ? "T00:00:00" : "")).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "—";

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
          <div className="panel-head"><h3>Work breakdown structure</h3><button type="button" className="button compact" disabled={busy} onClick={() => setShowWbsForm(!showWbsForm)}>{showWbsForm ? "Cancel" : "Add WBS item"}</button></div>
          {showWbsForm && <form className="planning-filters" onSubmit={addWbsItem}>
            <input required value={wbsName} onChange={e => setWbsName(e.target.value)} placeholder="Work item name" aria-label="WBS item name" />
            <input value={wbsCode} onChange={e => setWbsCode(e.target.value)} placeholder="Code (optional)" aria-label="WBS item code" />
            <input value={wbsSection} onChange={e => setWbsSection(e.target.value)} placeholder="Work section" aria-label="WBS work section" />
            <button className="button primary compact" type="submit" disabled={busy}>Save item</button>
          </form>}
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
                    <th>Actions</th>
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
                      <td>{editingWbsId === row.id ? <input value={wbsDraft.name} onChange={e => setWbsDraft({...wbsDraft,name:e.target.value})} aria-label="Edit WBS item name" /> : (row.work_section || "—")}</td>
                      <td>{editingWbsId === row.id ? <div className="row gap"><button type="button" className="button compact" disabled={busy} onClick={() => saveWbsEdit(row)}>Save</button><button type="button" className="button compact" disabled={busy} onClick={() => setEditingWbsId(null)}>Cancel</button></div> : <button type="button" className="button compact" disabled={busy || !row.id} onClick={() => {setEditingWbsId(row.id || null);setWbsDraft({name:row.name || "",code:row.code || "",work_section:row.work_section || ""});}}>Edit</button>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="planning-gantt-section">
            <div className="panel-head planning-gantt-head">
              <div>
                <h3>Schedule timeline</h3>
                <p className="muted small">Gantt view based on saved or generated planned dates. Activities without dates remain in the register below.</p>
              </div>
              <span className="muted small">{datedActivities.length} dated activities</span>
            </div>
            <div className="planning-critical-summary" role="status"><strong>Critical path analysis</strong><span>{criticalPath.hasCycle ? "Dependency cycle detected — review predecessor links." : criticalPath.criticalIds.size ? `${criticalPath.criticalIds.size} critical activities · ${criticalPath.duration} duration days (calendar dates and holidays are not adjusted)` : "Add valid predecessor links and activity durations to calculate the critical path."}</span></div>
            <div className="planning-filters">
              <input type="search" value={activitySearch} onChange={(e) => setActivitySearch(e.target.value)} placeholder="Search activity, code, section…" aria-label="Search schedule activities" />
              <select value={activityFilter} onChange={(e) => setActivityFilter(e.target.value)} aria-label="Filter schedule activities">
                <option value="all">All activities</option>
                <option value="not_started">Not started</option>
                <option value="in_progress">In progress</option>
                <option value="completed">Completed</option>
                <option value="overdue">Overdue</option>
              </select>
            </div>
            {datedActivities.length === 0 ? (
              <div className="empty empty-card planning-gantt-empty">
                <h3>No dated activities match</h3>
                <p>Generate a schedule from the estimate or adjust the filters. The timeline needs planned start and finish dates.</p>
              </div>
            ) : (
              <div className="planning-gantt-scroll">
                <div className="planning-gantt">
                  <div className="planning-gantt-axis">
                    <div className="planning-gantt-name">Activity</div>
                    <div className="planning-gantt-track-axis">
                      <span>{dateLabel(new Date(timelineStart).toISOString().slice(0,10))}</span>
                      <span>{dateLabel(new Date(timelineStart + timelineDays * 86400000 / 2).toISOString().slice(0,10))}</span>
                      <span>{dateLabel(new Date(timelineEnd).toISOString().slice(0,10))}</span>
                    </div>
                  </div>
                  {datedActivities.map((activity, index) => {
                    const startOffset = Math.max(0, (Date.parse(activity.planned_start!) - timelineStart) / 86400000);
                    const duration = Math.max(1, (Date.parse(activity.planned_finish!) - Date.parse(activity.planned_start!)) / 86400000 + 1);
                    const left = (startOffset / timelineDays) * 100;
                    const width = Math.min(100 - left, (duration / timelineDays) * 100);
                    const pct = Math.max(0, Math.min(100, Number(activity.percent_complete || 0)));
                    const isOverdue = activity.planned_finish! < new Date().toISOString().slice(0,10) && pct < 100;
                    return (
                      <div className="planning-gantt-row" key={activity.id || activity.code || index}>
                        <div className="planning-gantt-name">
                          <strong>{activity.code || "—"}</strong>
                          <span title={activity.name || "Unnamed activity"}>{activity.name || "Unnamed activity"}</span>
                          <small>{dateLabel(activity.planned_start)} – {dateLabel(activity.planned_finish)}</small>
                        </div>
                        <div className="planning-gantt-track">
                          <div className={"planning-gantt-bar" + (isOverdue ? " is-overdue" : "") + (activity.id && criticalPath.criticalIds.has(activity.id) ? " is-critical" : "")} style={{ left: left + "%", width: Math.max(1, width) + "%" }} title={(activity.name || "Activity") + ": " + pct + "% complete"}>
                            <span style={{ width: pct + "%" }} />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            <div className="planning-gantt-legend"><span><i /> Planned duration</span><span><i className="progress" /> Actual progress</span><span><i className="overdue" /> Overdue</span></div>
          </div>

          <div className="panel-head" style={{ marginTop: 24 }}><h3>Schedule &amp; progress</h3><button type="button" className="button compact" disabled={busy} onClick={() => setShowActivityForm(!showActivityForm)}>{showActivityForm ? "Cancel" : "Add activity"}</button></div>
          {showActivityForm && <form className="planning-filters" onSubmit={addActivity}>
            <input required value={activityDraft.name} onChange={e => setActivityDraft({...activityDraft,name:e.target.value})} placeholder="Activity name" aria-label="New activity name" />
            <input value={activityDraft.code} onChange={e => setActivityDraft({...activityDraft,code:e.target.value})} placeholder="Code (optional)" aria-label="New activity code" />
            <input value={activityDraft.work_section} onChange={e => setActivityDraft({...activityDraft,work_section:e.target.value})} placeholder="Work section" aria-label="New activity work section" />
            <label>Start <input type="date" value={activityDraft.planned_start} onChange={e => setActivityDraft({...activityDraft,planned_start:e.target.value})} /></label>
            <label>Finish <input type="date" value={activityDraft.planned_finish} onChange={e => setActivityDraft({...activityDraft,planned_finish:e.target.value})} /></label>
            <label>Duration (days) <input type="number" min="1" value={activityDraft.duration_days} onChange={e => setActivityDraft({...activityDraft,duration_days:e.target.value})} /></label>
            <input value={activityDraft.notes} onChange={e => setActivityDraft({...activityDraft,notes:e.target.value})} placeholder="Notes (optional)" aria-label="Activity notes" />
            <button className="button primary compact" type="submit" disabled={busy}>Save activity</button>
          </form>}
          {filteredActivities.length === 0 ? (
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
                    <th>Dependencies</th>
                    <th>Start</th>
                    <th>Finish</th>
                    <th>%</th>
                    <th>Status</th>
                    <th>Update</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredActivities.map((row, i) => (
                    <tr key={row.id || row.code || i}>
                      <td>
                        <code className="boq-code">{row.code || "—"}</code>
                      </td>
                      <td>{row.name || "—"}</td>
                      <td>{row.work_section || "—"}</td>
                      <td className="planning-dependency-cell">
                        {dependencyEditId === row.id ? (
                          <div className="planning-dependency-editor">
                            <select multiple value={selectedPredecessors} onChange={(e) => setSelectedPredecessors(Array.from(e.currentTarget.selectedOptions, (option) => option.value))} aria-label={"Predecessor activities for " + (row.name || row.code || "activity")}>
                              {activities.filter((candidate) => candidate.id && candidate.id !== row.id).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.code ? candidate.code + " — " : ""}{candidate.name || "Unnamed activity"}</option>)}
                            </select>
                            <small>Choose one or more predecessors (use Ctrl/long-press for multiple).</small>
                            <div className="row gap">
                              <button type="button" className="button compact" disabled={busy} onClick={() => saveDependencies(row)}>Save</button>
                              <button type="button" className="button compact" disabled={busy} onClick={() => setDependencyEditId(null)}>Cancel</button>
                            </div>
                          </div>
                        ) : (
                          <div className="planning-dependency-view">
                            <span>{(row.predecessor_ids || []).length ? (row.predecessor_ids || []).map((id) => activities.find((candidate) => candidate.id === id)?.code || activities.find((candidate) => candidate.id === id)?.name || "Unknown activity").join(", ") : "None"}</span>
                            <button type="button" className="button compact" disabled={busy || !row.id} onClick={() => startDependencies(row)}>Edit</button>
                          </div>
                        )}
                      </td>
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
