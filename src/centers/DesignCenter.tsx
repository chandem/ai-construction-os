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
  status?: string;
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
  source?: string | null;
  confidence?: number | null;
  properties?: Record<string, unknown> | null;
  notes?: string | null;
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
  const [qtoElements, setQtoElements] = React.useState<ElementRow[]>([]);
  const [quantities, setQuantities] = React.useState<QuantitySummary[]>([]);
  const [qtoSearch, setQtoSearch] = React.useState("");
  const [qtoStatusFilter, setQtoStatusFilter] = React.useState("all");
  const [qtoOriginFilter, setQtoOriginFilter] = React.useState("all");
  const [boq, setBoq] = React.useState<BoqRow[]>([]);
  const [estimate, setEstimate] = React.useState<EstimateSummary | null>(null);
  const [estimateRows, setEstimateRows] = React.useState<EstimateRow[]>([]);
  const [costIntel, setCostIntel] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [showElements, setShowElements] = React.useState(true);
  const [elementSearch, setElementSearch] = React.useState("");
  const [elementStatusFilter, setElementStatusFilter] = React.useState("all");
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
  const [boqSourceFilter, setBoqSourceFilter] = React.useState("all");
  const [hideLowConfidence, setHideLowConfidence] = React.useState(false);
  const [selectedBoqIds, setSelectedBoqIds] = React.useState<string[]>([]);
  const [bulkAccepting, setBulkAccepting] = React.useState(false);

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
      setQtoElements(quantityResult.data || []);
      setQuantities(quantityResult.summary || []);
      setBoq(boqResult.data || []);
      setEstimate(estimateResult.summary || null);
      setEstimateRows(estimateResult.data || []);
      try {
        setCostIntel(
          (await apiGet("/api/v1/projects/" + projectId + "/engineering/design-to-cost", token)).data || null
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

  async function deriveElementsFromBoq() {
    if (!projectId || !token || busy) return;
    if (!window.confirm("Create proposed engineering elements from the stored BOQ? Existing BOQ lines and estimate records will not be changed. Derived quantities and units will need engineering review.")) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await apiPost(
        "/api/v1/projects/" + projectId + "/engineering/elements/derive-from-boq",
        token,
      );
      setNotice("BOQ derivation completed: " + String(result.created || 0) +
        " new element(s), " + String(result.skipped || 0) + " already derived. Review all proposed quantities.");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not derive engineering elements from BOQ.");
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

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const quantityTotal = quantities.reduce((sum, row) => sum + Number(row.total_quantity || 0), 0);
  const quantityOrigin = (row: ElementRow) => {
    const method = String(row.properties?.quantity_method || "").toLowerCase();
    if (method === "explicit") return "source";
    if (method === "count_fallback") return "assumed";
    if (method === "insufficient" || !method || method === "unknown") return "unavailable";
    if (method.startsWith("dimension_")) return "measured";
    return "derived";
  };

  const quantityOriginLabel = (origin: string) => ({
    source: "Source-provided",
    measured: "Dimension-based",
    derived: "Formula-derived",
    assumed: "Assumed placeholder",
    unavailable: "Not available",
  }[origin] || "Not classified");

  const filteredQtoElements = React.useMemo(() => {
    const query = qtoSearch.trim().toLowerCase();
    return qtoElements.filter((row) => {
      const status = (row.status || "proposed").toLowerCase();
      if (qtoStatusFilter !== "all" && status !== qtoStatusFilter) return false;
      if (qtoOriginFilter !== "all" && quantityOrigin(row) !== qtoOriginFilter) return false;
      if (!query) return true;
      return [row.name, row.element_type, row.identifier, row.source, row.unit,
        row.properties?.quantity_method, row.properties?.quantity_notes,
        quantityOriginLabel(quantityOrigin(row))]
        .some((value) => String(value || "").toLowerCase().includes(query));
    });
  }, [qtoElements, qtoSearch, qtoStatusFilter, qtoOriginFilter]);
  const reviewCount = elements.filter((row) => (row.status || "proposed").toLowerCase() === "proposed").length;
  const filteredElements = React.useMemo(() => {
    const query = elementSearch.trim().toLowerCase();
    return elements.filter((row) => {
      const status = (row.status || "proposed").toLowerCase();
      if (elementStatusFilter !== "all" && status !== elementStatusFilter) return false;
      if (!query) return true;
      const sourceBoqId = String(row.properties?.source_boq_item_id || "");
      const linkedBoq = boq.find((item) => item.id === sourceBoqId);
      return [row.name, row.element_type, row.identifier, row.discipline, row.level,
        linkedBoq?.item_code, linkedBoq?.description]
        .some((value) => String(value || "").toLowerCase().includes(query));
    });
  }, [elements, boq, elementSearch, elementStatusFilter]);

  const sourceLabel = (source?: string | null) => {
    const value = String(source || "").toLowerCase();
    if (value.includes("document") || value.includes("import")) return "document";
    if (value.includes("quantity") || value.includes("takeoff") || value.includes("qto")) return "takeoff";
    if (value.includes("manual")) return "manual";
    if (value.includes("drawing")) return "drawing";
    return value || "other";
  };

  const confidenceValue = (row: BoqRow): number | null => {
    const raw = row.confidence ?? row.properties?.confidence;
    if (raw === null || raw === undefined || raw === "") return null;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) return null;
    return parsed > 1 ? Math.max(0, Math.min(1, parsed / 100)) : Math.max(0, Math.min(1, parsed));
  };

  const sourceOptions = React.useMemo(() => {
    const options = new Map<string, string>();
    boq.forEach((row) => {
      const key = sourceLabel(row.source);
      const label = key === "document" ? "Imported BOQ / document"
        : key === "takeoff" ? "Quantity takeoff"
        : key === "drawing" ? "Drawing takeoff"
        : key === "manual" ? "Manually entered"
        : key === "other" ? "Unspecified source"
        : String(row.source || key);
      options.set(key, label);
    });
    return Array.from(options.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [boq]);

  const filteredBoq = React.useMemo(() => {
    const q = boqSearch.trim().toLowerCase();
    return boq.filter((row) => {
      const status = (row.status || "proposed").toLowerCase();
      if (boqStatusFilter !== "all" && status !== boqStatusFilter) return false;
      if (boqSourceFilter !== "all" && sourceLabel(row.source) !== boqSourceFilter) return false;
      const confidence = confidenceValue(row);
      if (hideLowConfidence && confidence !== null && confidence < 0.5) return false;
      if (!q) return true;
      const hay = [row.item_code, row.description, row.work_section, row.unit, row.status, row.source]
        .map((x) => String(x || "").toLowerCase())
        .join(" ");
      return hay.includes(q);
    });
  }, [boq, boqSearch, boqStatusFilter, boqSourceFilter, hideLowConfidence]);

  const boqStatusCounts = React.useMemo(() => {
    const counts: Record<string, number> = { proposed: 0, approved: 0, rejected: 0 };
    for (const row of boq) {
      const s = (row.status || "proposed").toLowerCase();
      counts[s] = (counts[s] || 0) + 1;
    }
    return counts;
  }, [boq]);

  const importedBoqCount = React.useMemo(
    () => boq.filter((row) => String(row.source || "").includes("document")).length,
    [boq],
  );

  React.useEffect(() => {
    const visibleIds = new Set(filteredBoq.map((row) => row.id).filter(Boolean) as string[]);
    setSelectedBoqIds((current) => current.filter((id) => visibleIds.has(id)));
  }, [boqSearch, boqStatusFilter, boqSourceFilter, hideLowConfidence, boq]);

  function toggleBoqSelection(id: string, checked: boolean) {
    setSelectedBoqIds((current) => checked
      ? (current.includes(id) ? current : [...current, id])
      : current.filter((item) => item !== id));
  }

  async function bulkAcceptSelected() {
    const eligible = filteredBoq.filter((row) =>
      row.id && selectedBoqIds.includes(row.id) && (row.status || "proposed").toLowerCase() === "proposed"
    );
    if (!eligible.length || bulkAccepting) return;
    if (!window.confirm("Accept " + eligible.length + " selected proposed BOQ line(s)? This will save each line as approved.")) return;
    setBulkAccepting(true);
    setBusy(true);
    setError("");
    setNotice("");
    let accepted = 0;
    const failures: string[] = [];
    try {
      for (const row of eligible) {
        try {
          await apiPost(
            "/api/v1/projects/" + projectId + "/engineering/boq/items/" + row.id + "/review",
            token,
            {
              description: row.description || null,
              quantity: row.quantity ?? null,
              unit: row.unit || null,
              status: "approved",
            }
          );
          accepted += 1;
        } catch (e: any) {
          failures.push((row.item_code || row.description || row.id) + ": " + (e.message || "failed"));
        }
      }
      setSelectedBoqIds([]);
      if (failures.length) {
        setError("Accepted " + accepted + " line(s); " + failures.length + " failed. " + failures.slice(0, 3).join(" | "));
      } else {
        setNotice("Accepted " + accepted + " BOQ line(s).");
      }
      await load();
    } finally {
      setBulkAccepting(false);
      setBusy(false);
    }
  }

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
          <button
            type="button"
            className="button compact"
            disabled={loading || busy || boq.length === 0}
            onClick={deriveElementsFromBoq}
            title="Create proposed engineering elements from stored BOQ lines"
          >
            Derive elements from BOQ
          </button>
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
          {importedBoqCount > 0 && (
            <span className="muted small"> · {importedBoqCount} from documents</span>
          )}
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
            <button type="button" className="button compact" onClick={() => setShowElements((value) => !value)}>
              {showElements ? "Hide elements" : "Show elements"}
            </button>
          </div>

          {qtoElements.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div className="panel-head">
                <div>
                  <h3>Quantity Takeoff Review</h3>
                  <p className="muted small">
                    {filteredQtoElements.length} of {qtoElements.length} elements · derived quantities are indicative until reviewed
                  </p>
                </div>
              </div>
              <div className="boq-toolbar row gap">
                <input
                  type="search"
                  aria-label="Search quantity takeoff"
                  placeholder="Search element, method, source…"
                  value={qtoSearch}
                  onChange={(e) => setQtoSearch(e.target.value)}
                  style={{ minWidth: 180, flex: 1 }}
                />
                <select
                  aria-label="Filter quantity takeoff review status"
                  value={qtoStatusFilter}
                  onChange={(e) => setQtoStatusFilter(e.target.value)}
                  style={{ minWidth: 145 }}
                >
                  <option value="all">All statuses</option>
                  <option value="proposed">Proposed</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
                <select
                  aria-label="Filter quantity origin"
                  value={qtoOriginFilter}
                  onChange={(e) => setQtoOriginFilter(e.target.value)}
                  style={{ minWidth: 165 }}
                >
                  <option value="all">All quantity origins</option>
                  <option value="source">Source-provided</option>
                  <option value="measured">Dimension-based</option>
                  <option value="derived">Formula-derived</option>
                  <option value="assumed">Assumed placeholder</option>
                  <option value="unavailable">Not available</option>
                </select>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Element</th>
                      <th>Quantity</th>
                      <th>Unit</th>
                      <th>Quantity origin</th>
                      <th>Method</th>
                      <th>Confidence</th>
                      <th>Source</th>
                      <th>Review status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredQtoElements.slice(0, 50).map((row, index) => {
                      const rawConfidence = row.properties?.quantity_confidence;
                      const confidence = rawConfidence == null ? null : Number(rawConfidence);
                      const method = String(row.properties?.quantity_method || "unknown");
                      const origin = quantityOrigin(row);
                      return (
                        <tr key={row.id || row.identifier || index}>
                          <td>
                            <strong>{row.name || row.element_type || "Other"}</strong>
                            {row.identifier && <div className="muted small">{row.identifier}</div>}
                            {row.properties?.quantity_notes && (
                              <div className="muted small">{String(row.properties.quantity_notes)}</div>
                            )}
                          </td>
                          <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                          <td>{row.unit || "—"}</td>
                          <td>{quantityOriginLabel(origin)}</td>
                          <td><code>{method.replace(/_/g, " ")}</code></td>
                          <td>
                            {confidence === null || !Number.isFinite(confidence)
                              ? "—"
                              : Math.round(Math.max(0, Math.min(1, confidence)) * 100) + "%"}
                          </td>
                          <td>
                            {row.source_page ? "Page " + row.source_page : row.source || "Not recorded"}
                          </td>
                          <td>{statusBadge(row.status)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {filteredQtoElements.length > 50 && (
                  <p className="muted small">Showing first 50 matching takeoff elements.</p>
                )}
                {filteredQtoElements.length === 0 && (
                  <p className="muted small">No takeoff elements match these filters.</p>
                )}
              </div>
            </div>
          )}

          {chainEmpty ? (
            <div className="empty empty-card">
              <h3>No engineering data yet</h3>
              <p>
                Upload a drawing, specification, or BOQ PDF and wait until it is processed, then refresh.
                Generate BOQ from elements, or import lines from an uploaded BOQ document.
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
            <div style={{ marginTop: 16 }}>
              <div className="panel-head">
                <div>
                  <h3>Engineering Elements Review</h3>
                  <p className="muted small">{filteredElements.length} of {elements.length} elements · {reviewCount} proposed for review</p>
                </div>
              </div>
              <div className="boq-toolbar row gap">
                <input type="search" aria-label="Search engineering elements" placeholder="Search element, BOQ code or description…" value={elementSearch} onChange={(e) => setElementSearch(e.target.value)} style={{ minWidth: 180, flex: 1 }} />
                <select aria-label="Filter engineering element status" value={elementStatusFilter} onChange={(e) => setElementStatusFilter(e.target.value)} style={{ minWidth: 145 }}>
                  <option value="all">All statuses</option>
                  <option value="proposed">Proposed</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
              </div>
              <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Element</th>
                    <th>Identifier</th>
                    <th>Qty</th>
                    <th>Unit</th>
                    <th>Linked BOQ item</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Confidence</th>
                    <th>Review</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredElements.slice(0, 50).map((row, index) => {
                    const sourceBoqId = String(row.properties?.source_boq_item_id || "");
                    const linkedBoq = boq.find((item) => item.id === sourceBoqId);
                    return (
                    <tr key={row.id || index}>
                      <td>{row.name || row.element_type || "Other"}</td>
                      <td>{row.identifier || "—"}</td>
                      <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                      <td>{row.unit || "—"}</td>
                      <td>{linkedBoq ? <><strong>{linkedBoq.item_code || "BOQ"}</strong><div className="muted small">{linkedBoq.description || "—"}</div><div className="muted small">{linkedBoq.quantity ?? "—"} {linkedBoq.unit || ""}</div></> : sourceBoqId ? "BOQ item " + sourceBoqId : "—"}</td>
                      <td>{row.source_page ? "Page " + row.source_page : row.source || "AI"}</td>
                      <td><span className="status">{row.status || "proposed"}</span></td>
                      <td>
                        {row.confidence == null ? "—" : Math.round(Number(row.confidence) * 100) + "%"}
                      </td>
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
                            {(row.status || "proposed") === "approved" ? "Reviewed" : "Review"}
                          </button>
                        )}
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
              {filteredElements.length > 50 && <p className="muted small">Showing first 50 matching elements.</p>}
              {filteredElements.length === 0 && <p className="muted small">No engineering elements match these filters.</p>}
              </div>
            </div>
          )}

          {boq.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div className="panel-head">
                <div>
                  <h3>Proposed BOQ</h3>
                  <p className="muted small">
                    {boq.length} lines · {boqStatusCounts.proposed || 0} proposed ·{" "}
                    {boqStatusCounts.approved || 0} approved · {boqStatusCounts.rejected || 0} rejected
                    {importedBoqCount > 0 ? ` · ${importedBoqCount} imported from uploaded BOQ` : ""}
                  </p>
                </div>
              </div>
              <div className="boq-toolbar row gap">
                <input type="search" aria-label="Search BOQ" placeholder="Search code, description, section…" value={boqSearch} onChange={(e) => setBoqSearch(e.target.value)} style={{ minWidth: 180, flex: 1 }} />
                <select aria-label="Filter BOQ source" value={boqSourceFilter} onChange={(e) => setBoqSourceFilter(e.target.value)} style={{ minWidth: 155 }}>
                  <option value="all">All sources</option>
                  {sourceOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <select aria-label="Filter BOQ status" value={boqStatusFilter} onChange={(e) => setBoqStatusFilter(e.target.value)} style={{ width: 140 }}>
                  <option value="all">All statuses</option>
                  <option value="proposed">Proposed</option>
                  <option value="approved">Approved</option>
                  <option value="rejected">Rejected</option>
                </select>
                <label className="row gap small" style={{ alignItems: "center" }}>
                  <input type="checkbox" checked={hideLowConfidence} onChange={(e) => setHideLowConfidence(e.target.checked)} />
                  Hide low confidence (&lt;50%)
                </label>
              </div>
              <div className="row gap" style={{ justifyContent: "space-between", alignItems: "center", margin: "10px 0" }}>
                <label className="row gap small" style={{ alignItems: "center" }}>
                  <input
                    type="checkbox"
                    aria-label="Select all visible proposed BOQ lines"
                    checked={filteredBoq.filter((row) => row.id && (row.status || "proposed").toLowerCase() === "proposed").length > 0 &&
                      filteredBoq.filter((row) => row.id && (row.status || "proposed").toLowerCase() === "proposed").every((row) => selectedBoqIds.includes(row.id!))}
                    onChange={(e) => {
                      const ids = filteredBoq.filter((row) => row.id && (row.status || "proposed").toLowerCase() === "proposed").map((row) => row.id!);
                      setSelectedBoqIds((current) => e.target.checked
                        ? Array.from(new Set([...current, ...ids]))
                        : current.filter((id) => !ids.includes(id)));
                    }}
                  />
                  Select visible proposed lines
                </label>
                <div className="row gap" style={{ alignItems: "center" }}>
                  <span className="muted small">{selectedBoqIds.length} selected</span>
                  <button type="button" className="button primary compact" disabled={busy || bulkAccepting || !filteredBoq.some((row) => row.id && selectedBoqIds.includes(row.id) && (row.status || "proposed").toLowerCase() === "proposed")} onClick={bulkAcceptSelected}>
                    {bulkAccepting ? "Accepting…" : "Accept selected"}
                  </button>
                </div>
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
                        <th>Select</th>
                        <th>Code</th>
                        <th>Description</th>
                        <th>Section</th>
                        <th>Source</th>
                        <th>Confidence</th>
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
                            <input
                              type="checkbox"
                              aria-label={"Select BOQ line " + (row.item_code || row.description || index + 1)}
                              disabled={!row.id || (row.status || "proposed").toLowerCase() !== "proposed"}
                              checked={Boolean(row.id && selectedBoqIds.includes(row.id))}
                              onChange={(e) => row.id && toggleBoqSelection(row.id, e.target.checked)}
                            />
                          </td>
                          <td><code className="boq-code">{row.item_code || "—"}</code></td>
                          <td>{row.description || "—"}</td>
                          <td>{row.work_section || "—"}</td>
                          <td>
                            <span className="status" title={row.notes || row.source || ""}>
                              {String(row.source || "").includes("document")
                                ? "Document"
                                : String(row.source || "").includes("quantity") || String(row.source || "").includes("takeoff")
                                  ? "Takeoff"
                                  : row.source || "BOQ"}
                            </span>
                          </td>
                          <td>
                            {confidenceValue(row) === null ? <span className="muted" title="No confidence score was provided">Not available</span>
                              : <span className={"status " + (confidenceValue(row)! >= 0.8 ? "status-approved" : confidenceValue(row)! >= 0.5 ? "status-proposed" : "status-rejected")}>
                                {Math.round(confidenceValue(row)! * 100)}%
                              </span>}
                          </td>
                          <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                          <td>{row.unit || "—"}</td>
                          <td>{statusBadge(row.status)}</td>
                          <td>
                            {editingBoqId === row.id ? (
                              <div className="row gap">
                                <input aria-label="BOQ description" value={boqDescription} onChange={(e) => setBoqDescription(e.target.value)} style={{ minWidth: 120 }} />
                                <input aria-label="BOQ quantity" type="number" min="0" step="any" value={boqQuantity} onChange={(e) => setBoqQuantity(e.target.value)} style={{ width: 90 }} />
                                <input aria-label="BOQ unit" value={boqUnit} onChange={(e) => setBoqUnit(e.target.value)} style={{ width: 65 }} />
                                <select aria-label="BOQ status" value={boqStatus} onChange={(e) => setBoqStatus(e.target.value)} style={{ width: 100 }}>
                                  <option value="approved">Approved</option>
                                  <option value="proposed">Proposed</option>
                                  <option value="rejected">Rejected</option>
                                </select>
                                <button type="button" className="button compact" disabled={busy} onClick={() => saveBoqReview(row)}>Save</button>
                                <button type="button" className="button compact" disabled={busy} onClick={() => setEditingBoqId(null)}>Cancel</button>
                              </div>
                            ) : (
                              <button type="button" className="button compact" disabled={busy || !row.id} onClick={() => startBoqEdit(row)}>Review</button>
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
                Upload a BOQ PDF from the menu (then reprocess), or click Generate BOQ to turn engineering quantities into bill lines for commercial review.
              </p>
            </div>
          )}

          {estimateRows.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <div className="panel-head">
                <div>
                  <h3>Provisional estimate</h3>
                  <p className="muted small">Rates remain advisory until approved by a qualified professional.</p>
                </div>
              </div>
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
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {estimateRows.slice(0, 100).map((row, index) => (
                      <tr key={row.id || row.item_code || index}>
                        <td>{row.item_code || "—"}</td>
                        <td>{row.description || "—"}</td>
                        <td>{row.quantity == null ? "—" : Number(row.quantity).toLocaleString()}</td>
                        <td>{row.unit || "—"}</td>
                        <td>{row.unit_rate == null ? "—" : Number(row.unit_rate).toLocaleString()}</td>
                        <td>{row.amount == null ? "—" : Number(row.amount).toLocaleString()}</td>
                        <td>
                          {editingRateId === row.id ? (
                            <div className="row gap">
                              <input type="number" min="0" step="any" value={editRate} onChange={(e) => setEditRate(e.target.value)} style={{ width: 90 }} />
                              <input value={editCurrency} onChange={(e) => setEditCurrency(e.target.value)} style={{ width: 70 }} />
                              <button type="button" className="button compact" disabled={busy} onClick={() => saveRate(row)}>Save</button>
                              <button type="button" className="button compact" disabled={busy} onClick={() => setEditingRateId(null)}>Cancel</button>
                            </div>
                          ) : (
                            <button type="button" className="button compact" disabled={busy || !row.id} onClick={() => startRateEdit(row)}>
                              {row.rate_source === "project_rate" ? "Edit rate" : "Set rate"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!loading && boq.length > 0 && estimateRows.length === 0 && (
            <div className="empty empty-card" style={{ marginTop: 20 }}>
              <h3>BOQ ready — no estimate yet</h3>
              <p>Generate an estimate after reviewing the BOQ.</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}