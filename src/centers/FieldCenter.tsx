import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };

type DiaryRow = {
  id?: string;
  entry_date?: string;
  weather?: string;
  work_summary?: string;
  workforce_on_site?: number | null;
  equipment_on_site?: string;
  issues?: string;
  safety_notes?: string;
  work_section?: string;
  status?: string;
};

type ProgressRow = {
  id?: string;
  report_date?: string;
  activity_name?: string;
  activity_code?: string;
  percent_complete?: number;
  note?: string;
  status?: string;
};

const WEATHER = ["clear", "cloudy", "rain", "storm", "hot", "cold", "windy", "other"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function FieldCenter({ projectId, token }: Props) {
  const [summary, setSummary] = React.useState<any>(null);
  const [diary, setDiary] = React.useState<DiaryRow[]>([]);
  const [progress, setProgress] = React.useState<ProgressRow[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");

  const [entryDate, setEntryDate] = React.useState(todayIso());
  const [weather, setWeather] = React.useState("clear");
  const [workSection, setWorkSection] = React.useState("");
  const [workSummary, setWorkSummary] = React.useState("");
  const [workforce, setWorkforce] = React.useState("");
  const [equipment, setEquipment] = React.useState("");
  const [issues, setIssues] = React.useState("");
  const [safety, setSafety] = React.useState("");

  async function load() {
    if (!projectId || !token) return;
    setLoading(true);
    setError("");
    try {
      const [sum, d, p] = await Promise.all([
        apiGet("/api/v1/projects/" + projectId + "/field/summary", token),
        apiGet("/api/v1/projects/" + projectId + "/field/diary", token),
        apiGet("/api/v1/projects/" + projectId + "/field/progress", token),
      ]);
      setSummary(sum.data || sum);
      setDiary(d.data || []);
      setProgress(p.data || []);
      if (d.warning || p.warning) {
        setNotice(
          [d.warning, p.warning].filter(Boolean).join(" ") ||
            "Apply supabase/field.sql if diary tables are missing."
        );
      }
    } catch (e: any) {
      setError(e.message || "Could not load Field Center.");
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  async function submitDiary(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !token || busy) return;
    if (!workSummary.trim()) {
      setError("Enter a work summary for the site diary.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const body = {
        entry_date: entryDate || todayIso(),
        weather,
        work_summary: workSummary.trim(),
        work_section: workSection.trim() || null,
        workforce_on_site: workforce.trim() === "" ? null : Number(workforce),
        equipment_on_site: equipment.trim() || null,
        issues: issues.trim() || null,
        safety_notes: safety.trim() || null,
      };
      const result = await apiPost("/api/v1/projects/" + projectId + "/field/diary", token, body);
      if (result.warning) {
        setNotice(result.warning);
      } else {
        setNotice("Site diary entry submitted.");
      }
      setWorkSummary("");
      setIssues("");
      setSafety("");
      setEquipment("");
      setWorkforce("");
      await load();
    } catch (err: any) {
      setError(err.message || "Could not save diary entry.");
    } finally {
      setBusy(false);
    }
  }

  const overall = summary?.overall_percent_complete;

  return (
    <section className="panel field-center">
      <div className="panel-head">
        <div>
          <h2>Field Center</h2>
          <p className="muted small">
            Site diary and progress for general construction — buildings, civil, or mixed packages.
          </p>
        </div>
        <button type="button" className="button compact" disabled={loading || busy} onClick={load}>
          Refresh
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="center-summary">
        <div className="hint">
          <b>Diary entries</b>
          <span> · {summary?.diary_count ?? diary.length}</span>
        </div>
        <div className="hint">
          <b>Progress updates</b>
          <span> · {summary?.progress_update_count ?? progress.length}</span>
        </div>
        <div className="hint">
          <b>Overall progress</b>
          <span> · {overall == null ? "—" : overall + "%"}</span>
        </div>
      </div>

      <div className="field-layout">
        <form className="field-form" onSubmit={submitDiary}>
          <h3>New site diary</h3>
          <p className="muted small">Record what happened on site today for any work package.</p>

          <div className="field-grid">
            <label>
              Date
              <input type="date" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} />
            </label>
            <label>
              Weather
              <select value={weather} onChange={(e) => setWeather(e.target.value)}>
                {WEATHER.map((w) => (
                  <option key={w} value={w}>
                    {w}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Work section
              <input
                type="text"
                value={workSection}
                onChange={(e) => setWorkSection(e.target.value)}
                placeholder="e.g. Substructure, Road chainage 2+000"
              />
            </label>
            <label>
              Workforce on site
              <input
                type="number"
                min={0}
                value={workforce}
                onChange={(e) => setWorkforce(e.target.value)}
                placeholder="Headcount"
              />
            </label>
          </div>

          <label>
            Work summary
            <textarea
              rows={3}
              value={workSummary}
              onChange={(e) => setWorkSummary(e.target.value)}
              placeholder="Describe works completed, locations, and outputs…"
              required
            />
          </label>

          <label>
            Equipment on site
            <input
              type="text"
              value={equipment}
              onChange={(e) => setEquipment(e.target.value)}
              placeholder="e.g. 2 excavators, 1 tower crane"
            />
          </label>

          <label>
            Issues / delays
            <textarea
              rows={2}
              value={issues}
              onChange={(e) => setIssues(e.target.value)}
              placeholder="Access, materials, weather impact, coordination…"
            />
          </label>

          <label>
            Safety notes
            <textarea
              rows={2}
              value={safety}
              onChange={(e) => setSafety(e.target.value)}
              placeholder="Toolbox talk, incidents, near misses…"
            />
          </label>

          <button type="submit" className="button primary compact" disabled={busy}>
            {busy ? "Saving…" : "Submit diary entry"}
          </button>
        </form>

        <div className="field-lists">
          <h3>Recent diary</h3>
          {loading ? (
            <p className="muted">Loading…</p>
          ) : diary.length === 0 ? (
            <div className="empty empty-card">
              <h3>No diary entries yet</h3>
              <p>Submit the form to record the first site day for this project.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Weather</th>
                    <th>Section</th>
                    <th>Summary</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {diary.slice(0, 20).map((row) => (
                    <tr key={row.id}>
                      <td>{row.entry_date || "—"}</td>
                      <td>{row.weather || "—"}</td>
                      <td>{row.work_section || "—"}</td>
                      <td>{row.work_summary || "—"}</td>
                      <td>
                        <span className={"status status-" + (row.status || "draft")}>
                          {row.status || "draft"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3 style={{ marginTop: 24 }}>Progress updates</h3>
          {progress.length === 0 ? (
            <p className="muted small">
              No progress % recorded yet. Generate a schedule in Planning, then post progress against
              activities.
            </p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Activity</th>
                    <th>%</th>
                    <th>Note</th>
                  </tr>
                </thead>
                <tbody>
                  {progress.slice(0, 15).map((row) => (
                    <tr key={row.id}>
                      <td>{row.report_date || "—"}</td>
                      <td>
                        {row.activity_code ? row.activity_code + " · " : ""}
                        {row.activity_name || "—"}
                      </td>
                      <td>{row.percent_complete == null ? "—" : row.percent_complete + "%"}</td>
                      <td>{row.note || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
