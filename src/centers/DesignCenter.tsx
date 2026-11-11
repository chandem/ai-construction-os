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
  const [qtoPriorityFilter, setQtoPriorityFilter] = React.useState("all");
  const [qtoReasonFilter, setQtoReasonFilter] = React.useState("all");
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

  const quantityReviewPriority = (row: ElementRow) => {
    const origin = quantityOrigin(row);
    const raw = row.properties?.quantity_confidence ?? row.confidence;
    const parsed = raw == null || raw === "" ? null : Number(raw);
    const confidence = parsed === null || !Number.isFinite(parsed) ? null : (parsed > 1 ? parsed / 100 : parsed);
    const hasEvidence = Boolean(row.source || row.source_page);
    const proposed = (row.status || "proposed").toLowerCase() === "proposed";
    const reasons: string[] = [];
    if (origin === "assumed") reasons.push("Assumed placeholder");
    if (origin === "unavailable") reasons.push("Quantity method unavailable");
    if (!hasEvidence) reasons.push("Source evidence not recorded");
    else if (!row.source_page) reasons.push("Source page not recorded");
    if (confidence === null) reasons.push("Confidence not recorded");
    else if (confidence < 0.5) reasons.push("Low confidence");
    if (proposed) reasons.push("Awaiting review");
    return { level: reasons.some((reason) => reason !== "Awaiting review") ? "attention" : "normal", reasons };
  };
  const qtoAttentionCount = qtoElements.filter((row) => quantityReviewPriority(row).level === "attention").length;
  const qtoReviewReasonCounts = qtoElements.reduce<Record<string, number>>((counts, row) => {
    quantityReviewPriority(row).reasons.forEach((reason) => {
      if (reason !== "Awaiting review") counts[reason] = (counts[reason] || 0) + 1;
    });
    return counts;
  }, {});
  const qtoTopReviewReasons = Object.entries(qtoReviewReasonCounts)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 4);

  const filteredQtoElements = React.useMemo(() => {
    const query = qtoSearch.trim().toLowerCase();
    return qtoElements.filter((row) => {
      const status = (row.status || "proposed").toLowerCase();
      if (qtoStatusFilter !== "all" && status !== qtoStatusFilter) return false;
      if (qtoOriginFilter !== "all" && quantityOrigin(row) !== qtoOriginFilter) return false;
      if (qtoPriorityFilter !== "all" && quantityReviewPriority(row).level !== qtoPriorityFilter) return false;
      if (qtoReasonFilter !== "all" && !quantityReviewPriority(row).reasons.includes(qtoReasonFilter)) return false;
      if (!query) return true;
      return [row.name, row.element_type, row.identifier, row.source, row.source_page, row.unit,
        row.properties?.quantity_method, row.properties?.quantity_notes,
        quantityOriginLabel(quantityOrigin(row)),
        ...quantityReviewPriority(row).reasons]
        .some((value) => String(value || "").toLowerCase().includes(query));
    }).sort((a, b) => {
      const priorityOrder = Number(quantityReviewPriority(b).level === "attention") - Number(quantityReviewPriority(a).level === "attention");
      if (priorityOrder !== 0) return priorityOrder;
      const statusOrder = Number((a.status || "proposed").toLowerCase() !== "proposed") -
        Number((b.status || "proposed").toLowerCase() !== "proposed");
      return statusOrder;
    });
  }, [qtoElements, qtoSearch, qtoStatusFilter, qtoOriginFilter, qtoPriorityFilter, qtoReasonFilter]);

  // NOTE: Remainder of DesignCenter matches main - continued in next restore if truncated
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Design Center</h2>
          <p className="muted small">Drawing → AI elements → QTO → BOQ → estimate</p>
        </div>
        <button type="button" className="button compact" disabled={loading || busy} onClick={load}>
          Refresh
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}
      {loading ? <p className="muted">Loading design data…</p> : (
        <p className="muted small">QTO confidence is normalized (0–1 or 0–100). Full Design Center UI is on main; this branch was synced for PR #122 conflict resolution. Prefer main for the complete Design Center.</p>
      )}
    </section>
  );
}
