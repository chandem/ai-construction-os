import React from "react";
import { apiGet, apiPost } from "../api";
import { supabase } from "../supabaseClient";

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

type PhotoEvidence = {
  id: string;
  project_id: string;
  diary_entry_id?: string | null;
  storage_path: string;
  caption?: string | null;
  work_section?: string | null;
  captured_at?: string | null;
  created_at?: string;
  preview_url?: string;
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

type ScheduleActivity = {
  id: string;
  code?: string;
  name?: string;
  work_section?: string;
  percent_complete?: number;
  status?: string;
};

const WEATHER = ["clear", "cloudy", "rain", "storm", "hot", "cold", "windy", "other"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function FieldCenter({ projectId, token }: Props) {
  const [summary, setSummary] = React.useState<any>(null);
  const [diary, setDiary] = React.useState<DiaryRow[]>([]);
  const [diarySectionFilter, setDiarySectionFilter] = React.useState("");
  const [diaryDateFilter, setDiaryDateFilter] = React.useState("");
  const [progress, setProgress] = React.useState<ProgressRow[]>([]);
  const [photos, setPhotos] = React.useState<PhotoEvidence[]>([]);
  const [photoFile, setPhotoFile] = React.useState<File | null>(null);
  const [photoCaption, setPhotoCaption] = React.useState("");
  const [photoSection, setPhotoSection] = React.useState("");
  const [photoDiaryId, setPhotoDiaryId] = React.useState("");
  const [photoBusy, setPhotoBusy] = React.useState(false);
  const [activities, setActivities] = React.useState<ScheduleActivity[]>([]);
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
  const [activityId, setActivityId] = React.useState("");
  const [progressPercent, setProgressPercent] = React.useState("0");
  const [progressNote, setProgressNote] = React.useState("");

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
      setActivityId((current) => schedule.some((activity: ScheduleActivity) => activity.id === current)
        ? current
        : schedule[0]?.id || "");
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

  async function loadPhotoEvidence() {
    if (!projectId || !token) return;
    const { data, error: queryError } = await supabase
      .from("field_photo_evidence")
      .select("id, project_id, diary_entry_id, storage_path, caption, work_section, captured_at, created_at")
      .eq("project_id", projectId)
      .order("created_at", { ascending: false })
      .limit(60);
    if (queryError) {
      setNotice((current) => current || "Photo evidence is not configured yet. Apply supabase/field_photo_evidence.sql.");
      return;
    }
    const records = (data || []) as PhotoEvidence[];
    const withUrls = await Promise.all(records.map(async (record) => {
      const { data: signed } = await supabase.storage
        .from("field-photo-evidence")
        .createSignedUrl(record.storage_path, 900);
      return { ...record, preview_url: signed?.signedUrl };
    }));
    setPhotos(withUrls);
  }

  async function submitPhoto(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !token || !photoFile || photoBusy) return;
    if (!photoFile.type.startsWith("image/")) {
      setError("Choose an image file (JPEG, PNG, or WebP).");
      return;
    }
    if (photoFile.size > 10 * 1024 * 1024) {
      setError("Each photo must be 10 MB or smaller.");
      return;
    }
    setPhotoBusy(true);
    setError("");
    setNotice("");
    let uploadedPath = "";
    try {
      const safeName = photoFile.name.replace(/[^a-zA-Z0-9._-]/g, "-").slice(-100) || "site-photo";
      uploadedPath = projectId + "/" + crypto.randomUUID() + "-" + safeName;
      const { error: uploadError } = await supabase.storage
        .from("field-photo-evidence")
        .upload(uploadedPath, photoFile, { contentType: photoFile.type, upsert: false });
      if (uploadError) throw uploadError;
      const { error: insertError } = await supabase.from("field_photo_evidence").insert({
        project_id: projectId,
        diary_entry_id: photoDiaryId || null,
        storage_path: uploadedPath,
        caption: photoCaption.trim() || null,
        work_section: photoSection.trim() || null,
        captured_at: new Date(photoFile.lastModified || Date.now()).toISOString(),
      });
      if (insertError) {
        await supabase.storage.from("field-photo-evidence").remove([uploadedPath]);
        uploadedPath = "";
        throw insertError;
      }
      setPhotoFile(null);
      setPhotoCaption("");
      setPhotoSection("");
      setPhotoDiaryId("");
      const input = document.getElementById("field-photo-file") as HTMLInputElement | null;
      if (input) input.value = "";
      setNotice("Site photo uploaded and linked to the project.");
      await loadPhotoEvidence();
    } catch (err: any) {
      setError(err.message || "Could not upload site photo. Check that photo evidence SQL has been applied and you are a project member.");
    } finally {
      setPhotoBusy(false);
    }
  }

  async function deletePhoto(record: PhotoEvidence) {
    if (!window.confirm("Delete this site photo evidence? This cannot be undone.")) return;
    setError("");
    setNotice("");
    const { error: deleteError } = await supabase.from("field_photo_evidence").delete().eq("id", record.id);
    if (deleteError) {
      setError(deleteError.message || "Could not delete photo record.");
      return;
    }
    const { error: storageError } = await supabase.storage.from("field-photo-evidence").remove([record.storage_path]);
    if (storageError) {
      setNotice("Photo record deleted, but the stored image could not be removed. Ask an administrator to clean up storage.");
    } else {
      setNotice("Photo evidence deleted.");
    }
    await loadPhotoEvidence();
  }

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

  async function submitProgress(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId || !token || busy) return;
    if (!activityId) {
      setError("Select a scheduled activity before recording progress.");
      return;
    }
    const percent = Number(progressPercent);
    if (!Number.isFinite(percent) || percent < 0 || percent > 100) {
      setError("Progress must be between 0 and 100 percent.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost("/api/v1/projects/" + projectId + "/field/progress", token, {
        activity_id: activityId,
        percent_complete: percent,
        note: progressNote.trim() || null,
      });
      if (result.warning) {
        setNotice(result.warning);
      } else {
        setNotice(result.persisted === false
          ? "Progress was calculated, but could not be saved to the database."
          : "Progress update recorded.");
      }
      setProgressNote("");
      await load();
    } catch (err: any) {
      setError(err.message || "Could not save progress update.");
    } finally {
      setBusy(false);
    }
  }

  const overall = summary?.overall_percent_complete;
  const filteredDiary = diary.filter((row) => {
    const sectionMatches = !diarySectionFilter.trim()
      || (row.work_section || "").toLowerCase().includes(diarySectionFilter.trim().toLowerCase());
    const dateMatches = !diaryDateFilter || row.entry_date === diaryDateFilter;
    return sectionMatches && dateMatches;
  });

  function exportDiaryCsv() {
    const columns = [
      ["Date", "entry_date"],
      ["Weather", "weather"],
      ["Work section", "work_section"],
      ["Work summary", "work_summary"],
      ["Workforce", "workforce_on_site"],
      ["Equipment", "equipment_on_site"],
      ["Issues / delays", "issues"],
      ["Safety notes", "safety_notes"],
      ["Status", "status"],
    ] as const;
    const escapeCsv = (value: unknown) => {
      let text = value == null ? "" : String(value);
      if (/^[=+\-@\t\r]/.test(text)) text = "'" + text;
      return '"' + text.replace(/"/g, '""') + '"';
    };
    const rows = [
      columns.map(([label]) => escapeCsv(label)).join(","),
      ...filteredDiary.map((row) =>
        columns.map(([, key]) => escapeCsv(row[key as keyof DiaryRow])).join(",")
      ),
    ];
    const blob = new Blob(["\uFEFF" + rows.join("\r\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "site-diary-" + (diaryDateFilter || "all-dates") + ".csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

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
          <div className="diary-list-heading">
            <div>
              <h3>Site diary records</h3>
              <p className="muted small">{filteredDiary.length} of {diary.length} entries shown</p>
            </div>
            <button type="button" className="button compact" onClick={exportDiaryCsv} disabled={filteredDiary.length === 0}>
              Export CSV
            </button>
          </div>
          <div className="diary-filters">
            <label>
              Filter by work section
              <input
                type="search"
                value={diarySectionFilter}
                onChange={(e) => setDiarySectionFilter(e.target.value)}
                placeholder="Search section…"
              />
            </label>
            <label>
              Filter by date
              <input
                type="date"
                value={diaryDateFilter}
                onChange={(e) => setDiaryDateFilter(e.target.value)}
              />
            </label>
            {(diarySectionFilter || diaryDateFilter) && (
              <button
                type="button"
                className="button compact"
                onClick={() => { setDiarySectionFilter(""); setDiaryDateFilter(""); }}
              >
                Clear filters
              </button>
            )}
          </div>
          {loading ? (
            <p className="muted">Loading…</p>
          ) : diary.length === 0 ? (
            <div className="empty empty-card">
              <h3>No diary entries yet</h3>
              <p>Submit the form to record the first site day for this project.</p>
            </div>
          ) : filteredDiary.length === 0 ? (
            <div className="empty empty-card">
              <h3>No matching entries</h3>
              <p>Try another date or work-section filter.</p>
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
                  {filteredDiary.map((row) => (
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

          <section className="field-form photo-evidence-form">
            <h3>Site photo evidence</h3>
            <p className="muted small">Upload progress photos from the field and link them to a diary entry. Private project storage; images are shown with short-lived signed links.</p>
            <form onSubmit={submitPhoto}>
              <label>
                Photo (JPEG, PNG, or WebP; max 10 MB)
                <input id="field-photo-file" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => setPhotoFile(e.target.files?.[0] || null)} required />
              </label>
              <div className="field-grid">
                <label>
                  Work section
                  <input value={photoSection} onChange={(e) => setPhotoSection(e.target.value)} placeholder="e.g. Column C3, chainage 2+000" />
                </label>
                <label>
                  Link to diary entry (optional)
                  <select value={photoDiaryId} onChange={(e) => setPhotoDiaryId(e.target.value)}>
                    <option value="">No diary link</option>
                    {diary.filter((row) => row.id).map((row) => (
                      <option key={row.id} value={row.id}>{row.entry_date || "Undated"} · {(row.work_summary || "").slice(0, 65)}</option>
                    ))}
                  </select>
                </label>
              </div>
              <label>
                Caption / observation
                <textarea rows={2} value={photoCaption} onChange={(e) => setPhotoCaption(e.target.value)} placeholder="Describe visible work, location, or quality observation…" />
              </label>
              <button type="submit" className="button primary compact" disabled={photoBusy || busy || !photoFile}>
                {photoBusy ? "Uploading photo…" : "Upload photo evidence"}
              </button>
            </form>
            {photos.length === 0 ? (
              <p className="muted small">{loading ? "Loading photo evidence…" : "No photo evidence uploaded for this project yet."}</p>
            ) : (
              <div className="photo-evidence-grid">
                {photos.map((photo) => (
                  <article className="photo-evidence-card" key={photo.id}>
                    {photo.preview_url ? <a href={photo.preview_url} target="_blank" rel="noreferrer"><img src={photo.preview_url} alt={photo.caption || photo.work_section || "Construction site evidence"} loading="lazy" /></a> : <div className="photo-preview-unavailable">Preview unavailable</div>}
                    <div className="photo-evidence-copy">
                      <b>{photo.work_section || "Unspecified work section"}</b>
                      <p>{photo.caption || "No caption provided."}</p>
                      <small>{photo.created_at ? new Date(photo.created_at).toLocaleString() : "Date unavailable"}</small>
                      <button type="button" className="button compact" onClick={() => deletePhoto(photo)}>Delete</button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="field-form progress-entry-form">
            <h3>Record activity progress</h3>
            <p className="muted small">Update actual completion against a scheduled activity. This also attempts to update the activity's current completion in Planning.</p>
            {activities.length === 0 ? (
              <div className="hint">
                <b>No scheduled activities found.</b>
                <p className="muted small">Create a schedule in Planning first, then return here to record progress.</p>
                <button type="button" className="button compact" onClick={load} disabled={loading || busy}>Refresh activities</button>
              </div>
            ) : (
              <form onSubmit={submitProgress}>
                <label>
                  Scheduled activity
                  <select value={activityId} onChange={(e) => setActivityId(e.target.value)} required>
                    {activities.map((activity) => (
                      <option key={activity.id} value={activity.id}>
                        {(activity.code ? activity.code + " · " : "") + (activity.name || "Unnamed activity")}
                        {activity.work_section ? " — " + activity.work_section : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="field-grid">
                  <label>
                    Actual completion (%)
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.1}
                      value={progressPercent}
                      onChange={(e) => setProgressPercent(e.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Current planned status
                    <input
                      type="text"
                      value={activities.find((activity) => activity.id === activityId)?.status || "Not specified"}
                      readOnly
                    />
                  </label>
                </div>
                <label>
                  Progress note
                  <textarea
                    rows={2}
                    value={progressNote}
                    onChange={(e) => setProgressNote(e.target.value)}
                    placeholder="Describe completed quantities, constraints, or evidence…"
                  />
                </label>
                <button type="submit" className="button primary compact" disabled={busy || loading}>
                  {busy ? "Saving…" : "Record progress"}
                </button>
              </form>
            )}
          </section>

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
