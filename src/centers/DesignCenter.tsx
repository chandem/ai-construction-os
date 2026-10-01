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

type EstimateRow = {
  id?: string;
  item_code?: string;
  description?: string;
  quantity?: number | null;
  unit?: string | null;
  unit_rate?: number | null;
  amount?: number | null;
  currency?: string | null;
  status?: string;
  rate_source?: string | null;
};

export function DesignCenter({ projectId, token }: Props) {
  const [elements, setElements] = React.useState<ElementRow[]>([]);
  const [quantities, setQuantities] = React.useState<QuantitySummary[]>([]);
  const [boq, setBoq] = React.useState<BoqRow[]>([]);
  const [estimate, setEstimate] = React.useState<EstimateSummary | null>(null);
  const [estimateRows, setEstimateRows] = React.useState<EstimateRow[]>([]);
  const [costIntel, setCostIntel] = React.useState<any>(null);
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
  const [editingRateId, setEditingRateId] = React.useState<string | null>(null);
  const [editRate, setEditRate] = React.useState("");
  const [editCurrency, setEditCurrency] = React.useState("USD");
  const [boqSearch, setBoqSearch] = React.useState("");
  const [boqStatusFilter, setBoqStatusFilter] = React.useState("all");

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
      setEstimateRows(estimateResult.data || []);
      try {
        setCostIntel(
          (await apiGet("/api/v1/projects/" + projectId + "/engineering/design-to-cost", token)).data ||
            null
        );
      } catch {
        setCostIntel(null);
      }
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
    setEditStatus((row as any).status || "approved");
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
        { quantity, unit: editUnit.trim() || null, status: editStatus }
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
      await apiPost(
        "/api/v1/projects/" + projectId + "/engineering/boq/items/" + row.id + "/review",
        token,
        {
          description: boqDescription.trim() || null,
          quantity,
          unit: boqUnit.trim() || null,
          status: boqStatus,
        }
      );
      setEditingBoqId(null);
      setNotice("BOQ review saved.");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not save BOQ review.");
    } finally {
      setBusy(false);
    }
  }

  function startRateEdit(row: EstimateRow) {
    if (!row.id) return;
    setEditingRateId(row.id);
    setEditRate(row.unit_rate == null ? "" : String(row.unit_rate));
    setEditCurrency(row.currency || estimate?.currency || "USD");
    setError("");
    setNotice("");
  }

  async function saveRate(row: EstimateRow) {
    if (!row.id) return;
    const unitRate = Number(editRate);
    if (!Number.isFinite(unitRate) || unitRate < 0) {
      setError("Unit rate must be a valid non-negative number.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost("/api/v1/projects/" + projectId + "/estimate/items/" + row.id + "/rate", token, {
        unit_rate: unitRate,
        currency: editCurrency.trim() || "USD",
        status: "approved",
        rate_source: "project_rate",
      });
      setEditingRateId(null);
      setNotice("Estimate rate saved.");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not save estimate rate.");
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
      setNotice(
        label + " completed: " + String(result.persisted ?? result.data?.length ?? 0) + " item(s)."
      );
      await load();
    } catch (e: any) {
      setError(e.message || label + " failed.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const quantityTotal = quantities.reduce((sum, row) => sum + Number(row.total_quantity || 0), 0);
  const reviewCount = elements.filter((row) => Number(row.confidence ?? 0) < 0.7).length;

  const filteredBoq = React.useMemo(() => {
    const q = boqSearch.trim().toLowerCase();
    return boq.filter((row) => {
      const status = (row.status || "proposed").toLowerCase();
      if (boqStatusFilter !== "all" && status !== boqStatusFilter) return false;
      if (!q) return true;
      const hay = [row.item_code, row.description, row.work_section, row.unit, row.status]
        .map((x) => String(x || "").toLowerCase())
        .join(" ");
      return hay.includes(q);
    });
  }, [boq, boqSearch, boqStatusFilter]);

  const boqStatusCounts = React.useMemo(() => {
    const counts: Record<string, number> = { proposed: 0, approved: 0, rejected: 0 };
    for (const row of boq) {
      const s = (row.status || "proposed").toLowerCase();
      counts[s] = (counts[s] || 0) + 1;
    }
    return counts;
  }, [boq]);

  function statusBadge(status?: string) {
    const s = (status || "proposed").toLowerCase();
    const label = s.charAt(0).toUpperCase() + s.slice(1);
    return <span className={"status status-" + s}>{label}</span>;
  }

  const chainEmpty = !loading && elements.length === 0 && boq.length === 0;

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Design Center</h2>
          <p className="muted small">Drawing → AI elements → QTO → BOQ → estimate</p>
        </div>
        <div className="row gap">
          <button type="button" className="button compact" disabled={loading || busy} onClick={load}>
            Refresh
          </button>
          <button
            type="button"
            className="button primary compact"
            disabled={loading || busy}
            onClick={() => generate("/engineering/boq/generate", "BOQ generation")}
          >
            Generate BOQ
          </button>
          <button
            type="button"
            className="button primary compact"
            disabled={loading || busy}
            onClick={() => generate("/engineering/estimate/generate", "Estimate generation")}
          >
            Generate estimate
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="center-summary">
        <div className="hint">
          <b>Engineering elements</b>
          <span> · {elements.length}</span>
        </div>
        <div className="hint">
          <b>QTO groups</b>
          <span> · {quantities.length}</span>
        </div>
        <div className="hint">
          <b>Measured quantity</b>
          <span> · {quantityTotal.toLocaleString()}</span>
        </div>
        <div className="hint">
          <b>Review flags</b>
          <span> · {reviewCount}</span>
        </div>
        <div className="hint">
          <b>BOQ lines</b>
          <span> · {boq.length}</span>
        </div>
        {estimate && (
          <div className="hint">
            <b>Provisional estimate</b>
            <span>
              {" "}· {Number(estimate.total_amount || 0).toLocaleString()} {estimate.currency || ""}
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <p className="muted">Loading engineering data…</p>
      ) : (
        <>
          <div className="panel-head" style={{ marginTop: 16 }}>
            <div>
              <h3>Quantity Takeoff</h3>
              <p className="muted small">
                AI-derived quantities are proposed values and require professional review.
              </p>
            </div>
            <button
              type="button"
              className="button compact"
              onClick={() => setShowElements((value) => !value)}
            >
              {showElements ? "Hide elements" : "Show elements"}
            </button>
          </div>

          {chainEmpty ? (
            <div className="empty empty-card">
              <h3>No engineering data yet</h3>
              <p>
                Upload a drawing or specification, wait until it is processed, then refresh. Generate
                BOQ once elements exist.
              </p>
            </div>
          ) : quantities.length > 0 ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Element</th>
                    <th>Unit</th>
                    <th>Total</th>
                    <th>Items</th>
                  </tr>
                </thead>
                <tbody>
                  {quantities.map((row) => (
                    <tr key={row.element_type + row.unit}>
                      <td>{row.element_type}</td>
                      <td>{row.unit}</td>
                      <td>{Number(row.total_quantity).toLocaleString()}</td>
                      <td>{row.item_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty">
              <p>No engineering quantities yet. Upload a drawing/specification to create AI engineering elements.</p>
            </div>
          )}

          {showElements && elements.length > 0 && (
            <div className="table-wrap" style={{ marginTop: 16 }}>
              <table>
                <thead>
                  <tr>
                    <th>Element</th>
                    <th>Identifier</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Source</th>
                    <th>Confidence</th>
                    <th>Review</th>
                  </tr>
                </thead>
                <tbody>
                  {elements.slice(0, 50).map((row, index) => (
                    <tr key={row.id || index}>
                      <td>{row.name || row.element_type || "Other"}</td>
                      <td>{row.identifier || "—"}</td>
                      <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                      <td>{row.unit || "—"}</td>
                      <td>{row.source_page ? "Page " + row.source_page : row.source || "AI"}</td>
                      <td>
                        {row.confidence == null
                          ? "—"
                          : Math.round(Number(row.confidence) * 100) + "%"}
                      </td>
                      <td>
                        {editingId === row.id ? (
                          <div className="row gap">
                            <input
                              aria-label="Quantity"
                              type="number"
                              min="0"
                              step="any"
                              value={editQuantity}
                              onChange={(e) => setEditQuantity(e.target.value)}
                              style={{ width: 90 }}
                            />
                            <input
                              aria-label="Unit"
                              value={editUnit}
                              onChange={(e) => setEditUnit(e.target.value)}
                              style={{ width: 70 }}
                            />
                            <select
                              aria-label="Review status"
                              value={editStatus}
                              onChange={(e) => setEditStatus(e.target.value)}
                              style={{ width: 105 }}
                            >
                              <option value="approved">Approved</option>
                              <option value="proposed">Proposed</option>
                              <option value="rejected">Rejected</option>
                            </select>
                            <button
                              type="button"
                              className="button compact"
                              disabled={busy}
                              onClick={() => saveReview(row)}
                            >
                              Save
                            </button>
                            <button
                              type="button"
                              className="button compact"
                              disabled={busy}
                              onClick={() => setEditingId(null)}
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="button compact"
                            disabled={busy || !row.id}
                            onClick={() => startEdit(row)}
                          >
                            {(row as any).status === "approved" ? "Reviewed" : "Review"}
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
              <div className="panel-head">
                <div>
                  <h3>Proposed BOQ</h3>
                  <p className="muted small">
                    {boq.length} lines · {boqStatusCounts.proposed || 0} proposed ·{" "}
                    {boqStatusCounts.approved || 0} approved · {boqStatusCounts.rejected || 0}{" "}
                    rejected
                  </p>
                </div>
              </div>
              <div className="boq-toolbar row gap">
                <input
                  type="search"
                  aria-label="Search BOQ"
                  placeholder="Search code, description, section…"
                  value={boqSearch}
                  onChange={(e) => setBoqSearch(e.target.value)}
                  style={{ minWidth: 220, flex: 1 }}
                />
                <select
                  aria-label="Filter BOQ status"
                  value={boqStatusFilter}
                  onChange={(e) => setBoqStatusFilter(e.target.value)}
                  style={{ width: 140 }}
                >
                  <option value="all">All statuses</option>
                  <option value="proposed">Proposed</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              {filteredBoq.length === 0 ? (
                <div className="empty empty-card">
                  <h3>No matching BOQ lines</h3>
                  <p>Try a different search or status filter.</p>
                </div>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Section</th>
                        <th>Qty</th>
                        <th>Unit</th>
                        <th>Status</th>
                        <th>Review</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredBoq.map((row, index) => (
                        <tr key={row.id || row.item_code || index}>
                          <td>
                            <code className="boq-code">{row.item_code || "—"}</code>
                          </td>
                          <td>{row.description || "—"}</td>
                          <td>{row.work_section || "—"}</td>
                          <td>
                            {row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}
                          </td>
                          <td>{row.unit || "—"}</td>
                          <td>{statusBadge(row.status)}</td>
                          <td>
                            {editingBoqId === row.id ? (
                              <div className="row gap">
                                <input
                                  aria-label="BOQ description"
                                  value={boqDescription}
                                  onChange={(e) => setBoqDescription(e.target.value)}
                                  style={{ width: 180 }}
                                />
                                <input
                                  aria-label="BOQ quantity"
                                  type="number"
                                  min="0"
                                  step="any"
                                  value={boqQuantity}
                                  onChange={(e) => setBoqQuantity(e.target.value)}
                                  style={{ width: 90 }}
                                />
                                <input
                                  aria-label="BOQ unit"
                                  value={boqUnit}
                                  onChange={(e) => setBoqUnit(e.target.value)}
                                  style={{ width: 65 }}
                                />
                                <select
                                  aria-label="BOQ status"
                                  value={boqStatus}
                                  onChange={(e) => setBoqStatus(e.target.value)}
                                  style={{ width: 100 }}
                                >
                                  <option value="approved">Approved</option>
                                  <option value="proposed">Proposed</option>
                                  <option value="rejected">Rejected</option>
                                </select>
                                <button
                                  type="button"
                                  className="button compact"
                                  disabled={busy}
                                  onClick={() => saveBoqReview(row)}
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  className="button compact"
                                  disabled={busy}
                                  onClick={() => setEditingBoqId(null)}
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                className="button compact"
                                disabled={busy || !row.id}
                                onClick={() => startBoqEdit(row)}
                              >
                                Review
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {!loading && elements.length > 0 && boq.length === 0 && (
            <div className="empty empty-card" style={{ marginTop: 20 }}>
              <h3>Elements ready — no BOQ yet</h3>
              <p>
                Click Generate BOQ to turn engineering quantities into bill lines for commercial
                review.
              </p>
            </div>
          )}

          {costIntel && (
            <div style={{ marginTop: 20 }}>
              <h3>AI Design-to-Cost</h3>
              <p className="muted small">
                Cost concentration and what-if analysis for design review. Values remain provisional
                until project rates and quantities are approved.
              </p>
              <div className="center-summary">
                <div className="hint">
                  <b>Top cost drivers</b>
                  <span> · {(costIntel.cost_drivers || []).length}</span>
                </div>
                <div className="hint">
                  <b>80% Pareto lines</b>
                  <span> · {costIntel.pareto?.lines_needed ?? 0}</span>
                </div>
              </div>
              {(costIntel.cost_drivers || []).length > 0 && (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Item</th>
                        <th>Amount</th>
                        <th>Share</th>
                        <th>Focus</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(costIntel.cost_drivers || []).map((d: any, index: number) => (
                        <tr key={d.item_code || index}>
                          <td>{d.item_code || "—"}</td>
                          <td>{d.description || d.element_type || "Other"}</td>
                          <td>
                            {Number(d.amount || 0).toLocaleString()} {costIntel.currency || ""}
                          </td>
                          <td>{Number(d.share_pct || 0).toLocaleString()}%</td>
                          <td>{(costIntel.design_levers || [])[index]?.priority || "review"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {estimate && (
            <div style={{ marginTop: 20 }}>
              <h3>Estimate & Rate Review</h3>
              <p className="muted small">
                Enter project/tender rates before treating amounts as an estimate. Default AI rates
                are provisional.
              </p>
              {estimateRows.length > 0 ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Qty</th>
                        <th>Unit</th>
                        <th>Rate</th>
                        <th>Amount</th>
                        <th>Currency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {estimateRows.map((row, index) => (
                        <tr key={row.id || row.item_code || index}>
                          <td>{row.item_code || "—"}</td>
                          <td>{row.description || "—"}</td>
                          <td>
                            {row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}
                          </td>
                          <td>{row.unit || "—"}</td>
                          <td>
                            {editingRateId === row.id ? (
                              <input
                                aria-label="Unit rate"
                                type="number"
                                min="0"
                                step="any"
                                value={editRate}
                                onChange={(e) => setEditRate(e.target.value)}
                                style={{ width: 100 }}
                              />
                            ) : row.unit_rate == null ? (
                              "—"
                            ) : (
                              Number(row.unit_rate).toLocaleString()
                            )}
                          </td>
                          <td>{row.amount == null ? "—" : Number(row.amount).toLocaleString()}</td>
                          <td>
                            {editingRateId === row.id ? (
                              <div className="row gap">
                                <input
                                  aria-label="Currency"
                                  value={editCurrency}
                                  onChange={(e) => setEditCurrency(e.target.value)}
                                  style={{ width: 65 }}
                                />
                                <button
                                  type="button"
                                  className="button compact"
                                  disabled={busy}
                                  onClick={() => saveRate(row)}
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  className="button compact"
                                  disabled={busy}
                                  onClick={() => setEditingRateId(null)}
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                className="button compact"
                                disabled={busy || !row.id}
                                onClick={() => startRateEdit(row)}
                              >
                                {row.rate_source === "project_rate" ? "Edit rate" : "Set rate"}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty">
                  <p>Generate an estimate after reviewing the BOQ.</p>
                </div>
              )}
              <div className="hint" style={{ marginTop: 12 }}>
                <b>Estimate status</b>
                <span>
                  {" "}· {estimate.priced_lines ?? 0} priced lines, {estimate.unpriced_lines ?? 0}{" "}
                  unpriced lines. Rates are provisional and must be replaced with project/tender
                  rates.
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
