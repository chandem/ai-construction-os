import React from "react";
import { apiGet, apiPost } from "../api";
import { supabase } from "../supabaseClient";

type Props = { projectId: string; token: string };

type DiaryRow = {
  id?: string;
  entry_date?: string;
  work_summary?: string | null;
  weather?: string | null;
  workforce_on_site?: number | null;
  status?: string;
};

type ProgressRow = {
  id?: string;
  report_date?: string;
  activity_name?: string | null;
  activity_code?: string | null;
  percent_complete?: number | null;
  note?: string | null;
};

type ScheduleActivity = {
  id: string;
  code?: string | null;
  name?: string | null;
  percent_complete?: number | null;
};

type PhotoEvidence = {
  id: string;
  project_id: string;
  caption?: string | null;
  storage_path: string;
  created_at?: string;
};

export function FieldCenter({ projectId, token }: Props) {
  const [summary, setSummary] = React.useState<any>(null);
  const [diary, setDiary] = React.useState<DiaryRow[]>([]);
  const [progress, setProgress] = React.useState<ProgressRow[]>([]);
  const [activities, setActivities] = React.useState<ScheduleActivity[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");

  const [workSummary, setWorkSummary] = React.useState("");
  const [weather, setWeather] = React.useState("");
  const [workforce, setWorkforce] = React.useState("");
  const [activityId, setActivityId] = React.useState("");
  const [percent, setPercent] = React.useState("");
  const [progressNote, setProgressNote] = React.useState("");

  const [photos, setPhotos] = React.useState<PhotoEvidence[]>([]);
  const [photoBusy, setPhotoBusy] = React.useState(false);
  const [photoCaption, setPhotoCaption] = React.useState("");

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
      const schedule = sum.activities || sum.data?.activities || [];
      setActivities(schedule);
      setActivityId((current) =>
        schedule.some((activity: ScheduleActivity) => activity.id === current)
          ? current
          : schedule[0]?.id || "",
      );
      if (d.warning || p.warning || d.detail || p.detail) {
        setNotice(
          [d.warning, p.warning, d.detail, p.detail].filter(Boolean).join(" — ") ||
            "Apply supabase/field.sql if diary tables are missing.",
        );
      }
    } catch (e: any) {
      setError(e.message || "Could not load Field Center.");
    } finally {
      setLoading(false);
    }
  }

  async function loadPhotoEvidence() {
    if (!projectId) return;
    const { data, error: queryError } = await supabase
      .from("field_photo_evidence")
      .select("id,project_id,caption,storage_path,created_at")
      .eq("project_id", projectId)
      .order("created_at", { ascending: false });
    if (queryError) {
      // Photo evidence is optional until field_photo_evidence.sql is applied.
      setPhotos([]);
      return;
    }
    setPhotos((data as PhotoEvidence[]) || []);
  }

  React.useEffect(() => {
    load();
    loadPhotoEvidence();
  }, [projectId, token]);

  async function submitDiary(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !token || busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost("/api/v1/projects/" + projectId + "/field/diary", token, {
        work_summary: workSummary.trim() || null,
        weather: weather.trim() || null,
        workforce_on_site: workforce.trim() === "" ? null : Number(workforce),
      });
      if (result.warning) {
        setNotice(result.warning);
      } else {
        setNotice("Site diary entry saved.");
        setWorkSummary("");
        setWeather("");
        setWorkforce("");
      }
      await load();
    } catch (err: any) {
      setError(err.message || "Could not save diary entry.");
    } finally {
      setBusy(false);
    }
  }

  async function submitProgress(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !token || busy || !activityId) return;
    const pct = Number(percent);
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      setError("Percent complete must be between 0 and 100.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost("/api/v1/projects/" + projectId + "/field/progress", token, {
        activity_id: activityId,
        percent_complete: pct,
        note: progressNote.trim() || null,
      });
      if (result.warning) {
        setNotice(result.warning);
      } else {
        setNotice("Progress update recorded.");
        setPercent("");
        setProgressNote("");
      }
      await load();
    } catch (err: any) {
      setError(err.message || "Could not save progress update.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadPhoto(file: File) {
    if (!projectId || photoBusy) return;
    setPhotoBusy(true);
    setError("");
    try {
      const path = projectId + "/" + Date.now() + "-" + file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
      const { error: uploadError } = await supabase.storage
        .from("field-photo-evidence")
        .upload(path, file, { upsert: false });
      if (uploadError) throw uploadError;
      const { data: authData, error: authError } = await supabase.auth.getUser();
      if (authError || !authData.user) {
        throw new Error("Your Supabase session is not available. Sign out and sign in again, then retry the upload.");
      }
      const { error: insertError } = await supabase.from("field_photo_evidence").insert({
        project_id: projectId,
        caption: photoCaption.trim() || null,
        storage_path: path,
        created_by: authData.user.id,
      });
      if (insertError) throw insertError;
      setPhotoCaption("");
      setNotice("Photo evidence uploaded.");
      await loadPhotoEvidence();
    } catch (err: any) {
      setError(err.message || "Photo upload failed. Apply supabase/field_photo_evidence.sql if needed.");
    } finally {
      setPhotoBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Field Center</h2>
          <p className="muted small">Site diary, progress updates, and photo evidence</p>
        </div>
        <button type="button" className="button compact" disabled={loading || busy} onClick={load}>
          Refresh
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      {loading ? (
        <p className="muted">Loading field data…</p>
      ) : (
        <>
          <div className="center-summary">
            <div className="hint">
              <b>Diary entries</b>
              <span> · {diary.length}</span>
            </div>
            <div className="hint">
              <b>Progress updates</b>
              <span> · {progress.length}</span>
            </div>
            <div className="hint">
              <b>Schedule activities</b>
              <span> · {activities.length}</span>
            </div>
            {summary?.open_issues != null && (
              <div className="hint">
                <b>Open issues noted</b>
                <span> · {summary.open_issues}</span>
              </div>
            )}
          </div>

          <div className="field-layout">
            <form className="field-form" onSubmit={submitDiary}>
              <h3>New site diary entry</h3>
              <p className="muted small">Record work done on site today.</p>
              <label>Work summary</label>
              <textarea value={workSummary} onChange={(e) => setWorkSummary(e.target.value)} rows={3} />
              <div className="field-grid">
                <div>
                  <label>Weather</label>
                  <input value={weather} onChange={(e) => setWeather(e.target.value)} />
                </div>
                <div>
                  <label>Workforce on site</label>
                  <input type="number" min={0} value={workforce} onChange={(e) => setWorkforce(e.target.value)} />
                </div>
              </div>
              <button className="button primary compact" disabled={busy}>
                {busy ? "Saving…" : "Save diary entry"}
              </button>
            </form>

            <form className="field-form" onSubmit={submitProgress}>
              <h3>Progress update</h3>
              <p className="muted small">Update percent complete for a schedule activity.</p>
              <label>Activity</label>
              <select value={activityId} onChange={(e) => setActivityId(e.target.value)}>
                <option value="">Select activity</option>
                {activities.map((a) => (
                  <option key={a.id} value={a.id}>
                    {(a.code ? a.code + " — " : "") + (a.name || a.id)}
                  </option>
                ))}
              </select>
              <div className="field-grid">
                <div>
                  <label>Percent complete</label>
                  <input type="number" min={0} max={100} step="any" value={percent} onChange={(e) => setPercent(e.target.value)} />
                </div>
                <div>
                  <label>Note</label>
                  <input value={progressNote} onChange={(e) => setProgressNote(e.target.value)} />
                </div>
              </div>
              <button className="button primary compact" disabled={busy || !activityId}>
                {busy ? "Saving…" : "Record progress"}
              </button>
            </form>
          </div>

          {diary.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3>Recent diary</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Summary</th>
                      <th>Weather</th>
                      <th>Workforce</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {diary.slice(0, 20).map((row, i) => (
                      <tr key={row.id || i}>
                        <td>{row.entry_date || "—"}</td>
                        <td>{row.work_summary || "—"}</td>
                        <td>{row.weather || "—"}</td>
                        <td>{row.workforce_on_site ?? "—"}</td>
                        <td>{row.status || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {progress.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3>Recent progress</h3>
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
                    {progress.slice(0, 20).map((row, i) => (
                      <tr key={row.id || i}>
                        <td>{row.report_date || "—"}</td>
                        <td>{(row.activity_code ? row.activity_code + " — " : "") + (row.activity_name || "—")}</td>
                        <td>{row.percent_complete ?? "—"}</td>
                        <td>{row.note || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!loading && diary.length === 0 && progress.length === 0 && (
            <div className="empty empty-card" style={{ marginTop: 20 }}>
              <h3>No field records yet</h3>
              <p>Save a site diary entry or progress update to start tracking site activity.</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
