import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };

type Inspection = {
  id?: string;
  title?: string;
  inspection_type?: string;
  work_section?: string;
  result?: string;
  findings?: string;
  inspection_date?: string;
  status?: string;
};

type Ncr = {
  id?: string;
  ncr_code?: string;
  title?: string;
  severity?: string;
  work_section?: string;
  status?: string;
  raised_date?: string;
  description?: string;
};

type Incident = {
  id?: string;
  incident_code?: string;
  title?: string;
  incident_type?: string;
  severity?: string;
  status?: string;
  incident_date?: string;
};

const INSPECTION_TYPES = [
  "workmanship",
  "material",
  "hold_point",
  "witness_point",
  "final",
  "safety",
  "other",
];
const RESULTS = ["pass", "fail", "conditional", "pending"];
const SEVERITIES = ["minor", "major", "critical"];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function QualityCenter({ projectId, token }: Props) {
  const [summary, setSummary] = React.useState<any>(null);
  const [inspections, setInspections] = React.useState<Inspection[]>([]);
  const [ncrs, setNcrs] = React.useState<Ncr[]>([]);
  const [incidents, setIncidents] = React.useState<Incident[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [tab, setTab] = React.useState<"inspection" | "ncr">("inspection");

  const [inspTitle, setInspTitle] = React.useState("");
  const [inspType, setInspType] = React.useState("workmanship");
  const [inspResult, setInspResult] = React.useState("pending");
  const [inspSection, setInspSection] = React.useState("");
  const [inspFindings, setInspFindings] = React.useState("");

  const [ncrTitle, setNcrTitle] = React.useState("");
  const [ncrSeverity, setNcrSeverity] = React.useState("minor");
  const [ncrSection, setNcrSection] = React.useState("");
  const [ncrDesc, setNcrDesc] = React.useState("");

  async function load() {
    if (!projectId || !token) return;
    setLoading(true);
    setError("");
    try {
      const [sum, i, n, inc] = await Promise.all([
        apiGet("/api/v1/projects/" + projectId + "/quality/summary", token),
        apiGet("/api/v1/projects/" + projectId + "/quality/inspections", token),
        apiGet("/api/v1/projects/" + projectId + "/quality/ncrs", token),
        apiGet("/api/v1/projects/" + projectId + "/quality/incidents", token),
      ]);
      setSummary(sum.data || sum);
      setInspections(i.data || []);
      setNcrs(n.data || []);
      setIncidents(inc.data || []);
      const warn = [i.warning, n.warning, inc.warning].filter(Boolean).join(" ");
      if (warn) setNotice(warn);
    } catch (e: any) {
      setError(e.message || "Could not load Quality Center.");
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  async function submitInspection(e: React.FormEvent) {
    e.preventDefault();
    if (!inspTitle.trim()) {
      setError("Enter an inspection title.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const qs = new URLSearchParams({
        title: inspTitle.trim(),
        inspection_type: inspType,
        result: inspResult,
      });
      if (inspSection.trim()) qs.set("work_section", inspSection.trim());
      if (inspFindings.trim()) qs.set("findings", inspFindings.trim());
      const result = await apiPost(
        "/api/v1/projects/" + projectId + "/quality/inspections?" + qs.toString(),
        token
      );
      setNotice(result.warning || "Inspection recorded.");
      setInspTitle("");
      setInspFindings("");
      setInspSection("");
      setInspResult("pending");
      await load();
    } catch (err: any) {
      setError(err.message || "Could not save inspection.");
    } finally {
      setBusy(false);
    }
  }

  async function submitNcr(e: React.FormEvent) {
    e.preventDefault();
    if (!ncrTitle.trim()) {
      setError("Enter an NCR title.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const qs = new URLSearchParams({
        title: ncrTitle.trim(),
        severity: ncrSeverity,
      });
      if (ncrSection.trim()) qs.set("work_section", ncrSection.trim());
      if (ncrDesc.trim()) qs.set("description", ncrDesc.trim());
      const result = await apiPost(
        "/api/v1/projects/" + projectId + "/quality/ncrs?" + qs.toString(),
        token
      );
      setNotice(result.warning || "NCR raised.");
      setNcrTitle("");
      setNcrDesc("");
      setNcrSection("");
      await load();
    } catch (err: any) {
      setError(err.message || "Could not raise NCR.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel field-center">
      <div className="panel-head">
        <div>
          <h2>Quality Center</h2>
          <p className="muted small">
            Inspections and non-conformances for general construction works — any package or section.
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
          <b>Inspections</b>
          <span> · {summary?.inspection_count ?? inspections.length}</span>
        </div>
        <div className="hint">
          <b>NCRs open</b>
          <span> · {summary?.ncr_open ?? "—"}</span>
        </div>
        <div className="hint">
          <b>Incidents open</b>
          <span> · {summary?.incidents_open ?? "—"}</span>
        </div>
      </div>

      <div className="field-layout">
        <div className="field-form">
          <div className="row gap" style={{ marginBottom: 8 }}>
            <button
              type="button"
              className={"button compact" + (tab === "inspection" ? " primary" : "")}
              onClick={() => setTab("inspection")}
            >
              Inspection
            </button>
            <button
              type="button"
              className={"button compact" + (tab === "ncr" ? " primary" : "")}
              onClick={() => setTab("ncr")}
            >
              Raise NCR
            </button>
          </div>

          {tab === "inspection" ? (
            <form onSubmit={submitInspection}>
              <h3>Record inspection</h3>
              <p className="muted small">Hold points, workmanship, materials, or safety checks.</p>
              <label>
                Title
                <input
                  type="text"
                  value={inspTitle}
                  onChange={(e) => setInspTitle(e.target.value)}
                  placeholder="e.g. Concrete pour hold point — footing F2"
                  required
                />
              </label>
              <div className="field-grid">
                <label>
                  Type
                  <select value={inspType} onChange={(e) => setInspType(e.target.value)}>
                    {INSPECTION_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.replace(/_/g, " ")}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Result
                  <select value={inspResult} onChange={(e) => setInspResult(e.target.value)}>
                    {RESULTS.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label>
                Work section
                <input
                  type="text"
                  value={inspSection}
                  onChange={(e) => setInspSection(e.target.value)}
                  placeholder="e.g. Structure, Finishes, Earthworks"
                />
              </label>
              <label>
                Findings
                <textarea
                  rows={3}
                  value={inspFindings}
                  onChange={(e) => setInspFindings(e.target.value)}
                  placeholder="Observations, measurements, photos reference…"
                />
              </label>
              <button type="submit" className="button primary compact" disabled={busy}>
                {busy ? "Saving…" : "Save inspection"}
              </button>
            </form>
          ) : (
            <form onSubmit={submitNcr}>
              <h3>Raise NCR</h3>
              <p className="muted small">Non-conformance for defect or process deviation.</p>
              <label>
                Title
                <input
                  type="text"
                  value={ncrTitle}
                  onChange={(e) => setNcrTitle(e.target.value)}
                  placeholder="e.g. Rebar cover below specification"
                  required
                />
              </label>
              <div className="field-grid">
                <label>
                  Severity
                  <select value={ncrSeverity} onChange={(e) => setNcrSeverity(e.target.value)}>
                    {SEVERITIES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Work section
                  <input
                    type="text"
                    value={ncrSection}
                    onChange={(e) => setNcrSection(e.target.value)}
                    placeholder="Section / location"
                  />
                </label>
              </div>
              <label>
                Description
                <textarea
                  rows={3}
                  value={ncrDesc}
                  onChange={(e) => setNcrDesc(e.target.value)}
                  placeholder="What was found, where, and required corrective action…"
                />
              </label>
              <button type="submit" className="button primary compact" disabled={busy}>
                {busy ? "Saving…" : "Raise NCR"}
              </button>
            </form>
          )}
        </div>

        <div className="field-lists">
          <h3>Recent inspections</h3>
          {loading ? (
            <p className="muted">Loading…</p>
          ) : inspections.length === 0 ? (
            <div className="empty empty-card">
              <h3>No inspections yet</h3>
              <p>Record the first inspection for this project using the form.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Result</th>
                    <th>Section</th>
                  </tr>
                </thead>
                <tbody>
                  {inspections.slice(0, 15).map((row) => (
                    <tr key={row.id}>
                      <td>{row.inspection_date || "—"}</td>
                      <td>{row.title || "—"}</td>
                      <td>{(row.inspection_type || "—").replace(/_/g, " ")}</td>
                      <td>
                        <span className={"status status-" + (row.result || "pending")}>
                          {row.result || "pending"}
                        </span>
                      </td>
                      <td>{row.work_section || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3 style={{ marginTop: 24 }}>NCRs</h3>
          {ncrs.length === 0 ? (
            <p className="muted small">No non-conformances raised yet.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Title</th>
                    <th>Severity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {ncrs.slice(0, 12).map((row) => (
                    <tr key={row.id}>
                      <td>
                        <code className="boq-code">{row.ncr_code || "—"}</code>
                      </td>
                      <td>{row.title || "—"}</td>
                      <td>{row.severity || "—"}</td>
                      <td>
                        <span className={"status status-" + (row.status || "open")}>
                          {row.status || "open"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {incidents.length > 0 && (
            <>
              <h3 style={{ marginTop: 24 }}>Incidents</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Title</th>
                      <th>Type</th>
                      <th>Severity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {incidents.slice(0, 8).map((row) => (
                      <tr key={row.id}>
                        <td>
                          <code className="boq-code">{row.incident_code || "—"}</code>
                        </td>
                        <td>{row.title || "—"}</td>
                        <td>{(row.incident_type || "—").replace(/_/g, " ")}</td>
                        <td>{row.severity || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
