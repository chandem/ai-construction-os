import React from "react";
import { apiGet, apiPost } from "../api";

type Props = { projectId: string; token: string };

type ElementRow = {
  id?: string;
  element_type?: string;
  name?: string | null;
  identifier?: string | null;
  discipline?: string | null;
  level?: string | null;
  quantity?: number | null;
  unit?: string | null;
  source?: string | null;
  source_page?: number | null;
  confidence?: number | null;
  properties?: Record<string, unknown>;
};

type QuantitySummary = {
  element_type: string;
  unit: string;
  total_quantity: number;
  item_count: number;
};

type BoqRow = {
  item_code?: string;
  description?: string;
  work_section?: string;
  quantity?: number | null;
  unit?: string | null;
  item_count?: number;
  status?: string;
  id?: string;
};

type EstimateSummary = {
  total_amount?: number;
  currency?: string;
  priced_lines?: number;
  unpriced_lines?: number;
};

export function DesignCenter({ projectId, token }: Props) {
  const [elements, setElements] = React.useState<ElementRow[]>([]);
  const [quantities, setQuantities] = React.useState<QuantitySummary[]>([]);
  const [boq, setBoq] = React.useState<BoqRow[]>([]);
  const [estimate, setEstimate] = React.useState<EstimateSummary | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [showElements, setShowElements] = React.useState(true);
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [editQuantity, setEditQuantity] = React.useState("");
  const [editUnit, setEditUnit] = React.useState("");
  const [editStatus, setEditStatus] = React.useState("approved");
  const [editingBoqId, setEditingBoqId] = React.useState<string | null>(null);
  const [boqDescription, setBoqDescription] = React.useState("");
  const [boqQuantity, setBoqQuantity] = React.useState("");
  const [boqUnit, setBoqUnit] = React.useState("");
  const [boqStatus, setBoqStatus] = React.useState("approved");

  async function load() {
    if (!projectId || !token) return;
    setLoading(true);
    setError("");
    try {
      const [elementResult, quantityResult, boqResult, estimateResult] = await Promise.all([
        apiGet("/api/v1/projects/" + projectId + "/engineering/elements", token),
        apiGet("/api/v1/projects/" + projectId + "/engineering/quantities", token),
        apiGet("/api/v1/projects/" + projectId + "/engineering/boq", token),
        apiGet("/api/v1/projects/" + projectId + "/engineering/estimate", token),
      ]);
      setElements(elementResult.data || []);
      setQuantities(quantityResult.summary || []);
      setBoq(boqResult.data || []);
      setEstimate(estimateResult.summary || null);
    } catch (e: any) {
      setError(e.message || "Could not load Design Center.");
    } finally {
      setLoading(false);
    }
  }

  function startEdit(row: ElementRow) {
    if (!row.id) return;
    setEditingId(row.id);
    setEditQuantity(row.quantity == null ? "" : String(row.quantity));
    setEditUnit(row.unit || "");
    setEditStatus(row.status || "approved");
    setError("");
    setNotice("");
  }

  async function saveReview(row: ElementRow) {
    if (!row.id) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const quantity = editQuantity.trim() === "" ? null : Number(editQuantity);
      if (quantity !== null && (!Number.isFinite(quantity) || quantity < 0)) {
        throw new Error("Quantity must be a valid non-negative number.");
      }
      await apiPost(
        "/api/v1/projects/" + projectId + "/engineering/elements/" + row.id + "/review",
        token,
        { quantity, unit: editUnit.trim() || null, status: editStatus },
      );
      setEditingId(null);
      setNotice("Engineering element review saved.");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not save element review.");
    } finally {
      setBusy(false);
    }
  }

  function startBoqEdit(row: BoqRow) {
    if (!row.id) return;
    setEditingBoqId(row.id);
    setBoqDescription(row.description || "");
    setBoqQuantity(row.quantity == null ? "" : String(row.quantity));
    setBoqUnit(row.unit || "");
    setBoqStatus(row.status || "approved");
  }

  async function saveBoqReview(row: BoqRow) {
    if (!row.id) return;
    const quantity = boqQuantity.trim() === "" ? null : Number(boqQuantity);
    if (quantity !== null && (!Number.isFinite(quantity) || quantity < 0)) {
      setError("BOQ quantity must be a valid non-negative number.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost("/api/v1/projects/" + projectId + "/engineering/boq/items/" + row.id + "/review", token, {
        description: boqDescription.trim() || null,
        quantity,
        unit: boqUnit.trim() || null,
        status: boqStatus,
      });
      setEditingBoqId(null);
      setNotice("BOQ review saved.");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not save BOQ review.");
    } finally {
      setBusy(false);
    }
  }

  async function generate(path: string, label: string) {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost("/api/v1/projects/" + projectId + path, token);
      setNotice(label + " completed: " + String(result.persisted ?? result.data?.length ?? 0) + " item(s).");
      await load();
    } catch (e: any) {
      setError(e.message || label + " failed.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => { load(); }, [projectId, token]);

  const quantityTotal = quantities.reduce((sum, row) => sum + Number(row.total_quantity || 0), 0);
  const reviewCount = elements.filter((row) => Number(row.confidence ?? 0) < 0.7).length;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Design Center</h2>
          <p className="muted small">Drawing → AI elements → QTO → BOQ → estimate</p>
        </div>
        <div className="row gap">
          <button type="button" className="button compact" disabled={loading || busy} onClick={load}>Refresh</button>
          <button type="button" className="button primary compact" disabled={loading || busy} onClick={() => generate("/engineering/boq/generate", "BOQ generation")}>Generate BOQ</button>
          <button type="button" className="button primary compact" disabled={loading || busy} onClick={() => generate("/engineering/estimate/generate", "Estimate generation")}>Generate estimate</button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="center-summary">
        <div className="hint"><b>Engineering elements</b><span> · {elements.length}</span></div>
        <div className="hint"><b>QTO groups</b><span> · {quantities.length}</span></div>
        <div className="hint"><b>Measured quantity</b><span> · {quantityTotal.toLocaleString()}</span></div>
        <div className="hint"><b>Review flags</b><span> · {reviewCount}</span></div>
        <div className="hint"><b>BOQ lines</b><span> · {boq.length}</span></div>
        {estimate && <div className="hint"><b>Provisional estimate</b><span> · {Number(estimate.total_amount || 0).toLocaleString()} {estimate.currency || ""}</span></div>}
      </div>

      {loading ? <p className="muted">Loading engineering data…</p> : (
        <>
          <div className="panel-head" style={{ marginTop: 16 }}>
            <div>
              <h3>Quantity Takeoff</h3>
              <p className="muted small">AI-derived quantities are proposed values and require professional review.</p>
            </div>
            <button type="button" className="button compact" onClick={() => setShowElements((value) => !value)}>
              {showElements ? "Hide elements" : "Show elements"}
            </button>
          </div>

          {quantities.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Element</th><th>Unit</th><th>Total</th><th>Items</th></tr></thead>
                <tbody>
                  {quantities.map((row) => (
                    <tr key={row.element_type + row.unit}>
                      <td>{row.element_type}</td><td>{row.unit}</td><td>{Number(row.total_quantity).toLocaleString()}</td><td>{row.item_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <div className="empty"><p>No engineering quantities yet. Upload a drawing/specification to create AI engineering elements.</p></div>}

          {showElements && elements.length > 0 && (
            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead><tr><th>Element</th><th>Identifier</th><th>Qty</th><th>Unit</th><th>Source</th><th>Confidence</th><th>Review</th></tr></thead>
                <tbody>
                  {elements.slice(0, 50).map((row, index) => (
                    <tr key={row.id || index}>
                      <td>{row.name || row.element_type || "Other"}</td>
                      <td>{row.identifier || "—"}</td>
                      <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                      <td>{row.unit || "—"}</td>
                      <td>{row.source_page ? "Page " + row.source_page : row.source || "AI"}</td>
                      <td>{row.confidence == null ? "—" : Math.round(Number(row.confidence) * 100) + "%"}</td>
                      <td>
                        {editingId === row.id ? (
                          <div className="row gap">
                            <input aria-label="Quantity" type="number" min="0" step="any" value={editQuantity} onChange={(e) => setEditQuantity(e.target.value)} style={{ width: 90 }} />
                            <input aria-label="Unit" value={editUnit} onChange={(e) => setEditUnit(e.target.value)} style={{ width: 70 }} />
                            <select aria-label="Review status" value={editStatus} onChange={(e) => setEditStatus(e.target.value)} style={{ width: 105 }}>
                              <option value="approved">Approved</option>
                              <option value="proposed">Proposed</option>
                              <option value="rejected">Rejected</option>
                            </select>
                            <button type="button" className="button compact" disabled={busy} onClick={() => saveReview(row)}>Save</button>
                            <button type="button" className="button compact" disabled={busy} onClick={() => setEditingId(null)}>Cancel</button>
                          </div>
                        ) : (
                          <button type="button" className="button compact" disabled={busy || !row.id} onClick={() => startEdit(row)}>
                            {row.status === "approved" ? "Reviewed" : "Review"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {elements.length > 50 && <p className="muted small">Showing first 50 elements.</p>}
            </div>
          )}

          {boq.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3>Proposed BOQ</h3>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Code</th><th>Description</th><th>Section</th><th>Qty</th><th>Unit</th><th>Status</th><th>Review</th></tr></thead>
                  <tbody>
                    {boq.map((row, index) => (
                      <tr key={row.item_code || index}>
                        <td>{row.item_code || "—"}</td>
                        <td>{row.description || "—"}</td>
                        <td>{row.work_section || "—"}</td>
                        <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                        <td>{row.unit || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {estimate && (
            <div className="hint" style={{ marginTop: 16 }}>
              <b>Estimate status</b>
              <span> · {estimate.priced_lines ?? 0} priced lines, {estimate.unpriced_lines ?? 0} unpriced lines. Rates are provisional and must be replaced with project/tender rates.</span>
            </div>
          )}
        </>
      )}
    </section>
  );
}
