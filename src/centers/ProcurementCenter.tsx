import React from "react";
import { apiGet, apiPatch, apiPost } from "../api";

type Props = { projectId: string; token: string };

type Item = {
  id: string;
  item_code?: string | null;
  material_name: string;
  specification?: string | null;
  unit?: string | null;
  required_quantity?: number | null;
  requested_quantity?: number | null;
  ordered_quantity?: number | null;
  delivered_quantity?: number | null;
  supplier?: string | null;
  status?: string | null;
  required_date?: string | null;
};

const STATUS_LABELS: Record<string, string> = {
  planned: "Planned",
  requested: "Requested",
  ordered: "Ordered",
  partially_delivered: "Partially delivered",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export function ProcurementCenter({ projectId, token }: Props) {
  const [items, setItems] = React.useState<Item[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [edit, setEdit] = React.useState<Partial<Item>>({});
  const [search, setSearch] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("all");

  async function load() {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    try {
      const r = await apiGet("/api/v1/projects/" + projectId + "/procurement/items", token);
      setItems(r.data || []);
    } catch (e: any) {
      setError(e.message || "Could not load procurement.");
    } finally {
      setBusy(false);
      setLoading(false);
    }
  }

  function startEdit(i: Item) {
    setEditingId(i.id);
    setEdit({ ...i });
  }

  async function save() {
    if (!editingId) return;
    setBusy(true);
    setError("");
    try {
      await apiPatch("/api/v1/projects/" + projectId + "/procurement/items/" + editingId, token, {
        specification: edit.specification || null,
        requested_quantity: Number(edit.requested_quantity || 0),
        ordered_quantity: Number(edit.ordered_quantity || 0),
        delivered_quantity: Number(edit.delivered_quantity || 0),
        supplier: edit.supplier || null,
        status: edit.status || "planned",
        required_date: edit.required_date || null,
      });
      setNotice("Procurement item updated.");
      setEditingId(null);
      await load();
    } catch (e: any) {
      setError(e.message || "Could not update procurement item.");
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const r = await apiPost("/api/v1/projects/" + projectId + "/procurement/from-boq", token);
      const n = r.created ?? r.data?.length ?? 0;
      setNotice(n + " procurement requirement(s) created from approved BOQ lines.");
      await load();
    } catch (e: any) {
      setError(
        e.message ||
          "Could not generate requirements. Approve BOQ lines in Design first."
      );
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((i) => {
      const st = (i.status || "planned").toLowerCase();
      if (statusFilter !== "all" && st !== statusFilter) return false;
      if (!q) return true;
      const hay = [i.item_code, i.material_name, i.specification, i.supplier, i.status]
        .map((x) => String(x || "").toLowerCase())
        .join(" ");
      return hay.includes(q);
    });
  }, [items, search, statusFilter]);

  const totalReq = items.reduce((s, i) => s + Number(i.required_quantity || 0), 0);
  const totalDel = items.reduce((s, i) => s + Number(i.delivered_quantity || 0), 0);
  const byStatus = React.useMemo(() => {
    const m: Record<string, number> = {};
    for (const i of items) {
      const s = i.status || "planned";
      m[s] = (m[s] || 0) + 1;
    }
    return m;
  }, [items]);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Procurement Center</h2>
          <p className="muted small">
            Approved BOQ → material requirements → supplier and delivery tracking for any construction
            package.
          </p>
        </div>
        <div className="row gap">
          <button type="button" className="button compact" disabled={busy} onClick={load}>
            Refresh
          </button>
          <button type="button" className="button primary compact" disabled={busy} onClick={generate}>
            Generate from approved BOQ
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="center-summary">
        <div className="hint">
          <b>Requirements</b>
          <span> · {items.length}</span>
        </div>
        <div className="hint">
          <b>Total required</b>
          <span> · {totalReq.toLocaleString()}</span>
        </div>
        <div className="hint">
          <b>Delivered</b>
          <span> · {totalDel.toLocaleString()}</span>
        </div>
        <div className="hint">
          <b>Ordered</b>
          <span> · {byStatus.ordered || 0}</span>
        </div>
      </div>

      {loading && !items.length ? (
        <p className="muted">Loading procurement…</p>
      ) : items.length === 0 ? (
        <div className="empty empty-card">
          <h3>No procurement requirements yet</h3>
          <p>
            Approve BOQ lines in Design, then generate material requirements. Works for building,
            civil, or mixed packages.
          </p>
          <button type="button" className="button primary compact" disabled={busy} onClick={generate}>
            Generate from approved BOQ
          </button>
        </div>
      ) : (
        <>
          <div className="boq-toolbar row gap">
            <input
              type="search"
              aria-label="Search procurement"
              placeholder="Search material, code, supplier…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: 220, flex: 1 }}
            />
            <select
              aria-label="Filter status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ width: 180 }}
            >
              <option value="all">All statuses</option>
              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          {filtered.length === 0 ? (
            <div className="empty empty-card">
              <h3>No matching items</h3>
              <p>Try a different search or status filter.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Material</th>
                    <th>Required</th>
                    <th>Requested</th>
                    <th>Ordered</th>
                    <th>Delivered</th>
                    <th>Supplier</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((i) => (
                    <tr key={i.id}>
                      <td>
                        <code className="boq-code">{i.item_code || "—"}</code>
                      </td>
                      <td>
                        <b>{i.material_name}</b>
                        <br />
                        <small className="muted">{i.specification || "No specification"}</small>
                      </td>
                      <td>
                        {Number(i.required_quantity || 0).toLocaleString()} {i.unit || ""}
                      </td>
                      {editingId === i.id ? (
                        <>
                          <td>
                            <input
                              type="number"
                              min={0}
                              value={Number(edit.requested_quantity || 0)}
                              onChange={(e) =>
                                setEdit({ ...edit, requested_quantity: Number(e.target.value) })
                              }
                              style={{ width: 80 }}
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              min={0}
                              value={Number(edit.ordered_quantity || 0)}
                              onChange={(e) =>
                                setEdit({ ...edit, ordered_quantity: Number(e.target.value) })
                              }
                              style={{ width: 80 }}
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              min={0}
                              value={Number(edit.delivered_quantity || 0)}
                              onChange={(e) =>
                                setEdit({ ...edit, delivered_quantity: Number(e.target.value) })
                              }
                              style={{ width: 80 }}
                            />
                          </td>
                          <td>
                            <input
                              value={edit.supplier || ""}
                              onChange={(e) => setEdit({ ...edit, supplier: e.target.value })}
                              style={{ width: 120 }}
                            />
                          </td>
                          <td>
                            <select
                              value={edit.status || "planned"}
                              onChange={(e) => setEdit({ ...edit, status: e.target.value })}
                            >
                              {Object.entries(STATUS_LABELS).map(([k, v]) => (
                                <option key={k} value={k}>
                                  {v}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <div className="row gap">
                              <button
                                type="button"
                                className="button compact"
                                disabled={busy}
                                onClick={save}
                              >
                                Save
                              </button>
                              <button
                                type="button"
                                className="button compact"
                                onClick={() => setEditingId(null)}
                              >
                                Cancel
                              </button>
                            </div>
                          </td>
                        </>
                      ) : (
                        <>
                          <td>{Number(i.requested_quantity || 0).toLocaleString()}</td>
                          <td>{Number(i.ordered_quantity || 0).toLocaleString()}</td>
                          <td>{Number(i.delivered_quantity || 0).toLocaleString()}</td>
                          <td>{i.supplier || "—"}</td>
                          <td>
                            <span className={"status status-" + (i.status || "planned")}>
                              {STATUS_LABELS[i.status || "planned"] || i.status}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className="button compact"
                              disabled={busy}
                              onClick={() => startEdit(i)}
                            >
                              Update
                            </button>
                          </td>
                        </>
                      )}
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
