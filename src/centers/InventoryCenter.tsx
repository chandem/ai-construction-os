import React from "react";
import { apiGet, apiPatch, apiPost } from "../api";

type Props = { projectId: string; token: string };

type Item = {
  id: string;
  procurement_item_id?: string | null;
  item_code?: string | null;
  material_name: string;
  specification?: string | null;
  unit?: string | null;
  opening_quantity?: number | null;
  received_quantity?: number | null;
  consumed_quantity?: number | null;
  reserved_quantity?: number | null;
  reorder_level?: number | null;
  supplier?: string | null;
  location?: string | null;
};

type Insight = {
  inventory_item_id: string;
  material_name: string;
  available: number;
  reorder_level: number;
  shortage_to_reorder: number;
  priority: string;
  reason: string;
};

function availableQty(i: Item): number {
  return (
    Number(i.opening_quantity || 0) +
    Number(i.received_quantity || 0) -
    Number(i.consumed_quantity || 0) -
    Number(i.reserved_quantity || 0)
  );
}

export function InventoryCenter({ projectId, token }: Props) {
  const [items, setItems] = React.useState<Item[]>([]);
  const [insights, setInsights] = React.useState<Insight[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [edit, setEdit] = React.useState<Partial<Item>>({});
  const [search, setSearch] = React.useState("");
  const [lowOnly, setLowOnly] = React.useState(false);

  async function load() {
    if (!projectId || !token) return;
    setBusy(true);
    setError("");
    try {
      const [r, i] = await Promise.all([
        apiGet("/api/v1/projects/" + projectId + "/inventory/items", token),
        apiGet("/api/v1/projects/" + projectId + "/inventory/insights", token),
      ]);
      setItems(r.data || []);
      setInsights(i.data || []);
    } catch (e: any) {
      setError(e.message || "Could not load inventory.");
    } finally {
      setBusy(false);
      setLoading(false);
    }
  }

  async function save() {
    if (!editingId) return;
    setBusy(true);
    setError("");
    try {
      await apiPatch("/api/v1/projects/" + projectId + "/inventory/items/" + editingId, token, {
        opening_quantity: Number(edit.opening_quantity || 0),
        consumed_quantity: Number(edit.consumed_quantity || 0),
        reserved_quantity: Number(edit.reserved_quantity || 0),
        reorder_level: Number(edit.reorder_level || 0),
        location: edit.location || null,
      });
      setNotice("Inventory item updated.");
      setEditingId(null);
      await load();
    } catch (e: any) {
      setError(e.message || "Could not update inventory.");
    } finally {
      setBusy(false);
    }
  }

  async function issue(i: Item) {
    const raw = window.prompt("Quantity consumed / issued for " + i.material_name + ":", "1");
    if (raw === null) return;
    const qty = Number(raw);
    if (!Number.isFinite(qty) || qty <= 0) {
      setError("Enter a positive quantity.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await apiPost("/api/v1/projects/" + projectId + "/inventory/items/" + i.id + "/issue", token, {
        quantity: qty,
        notes: "Site material consumption",
      });
      setNotice(qty + " " + (i.unit || "units") + " issued from " + i.material_name + ".");
      await load();
    } catch (e: any) {
      setError(e.message || "Could not issue inventory.");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    load();
  }, [projectId, token]);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    const lowIds = new Set(insights.map((x) => x.inventory_item_id));
    return items.filter((i) => {
      if (lowOnly && !lowIds.has(i.id)) return false;
      if (!q) return true;
      const hay = [i.item_code, i.material_name, i.specification, i.location, i.supplier]
        .map((x) => String(x || "").toLowerCase())
        .join(" ");
      return hay.includes(q);
    });
  }, [items, search, lowOnly, insights]);

  const received = items.reduce((s, i) => s + Number(i.received_quantity || 0), 0);
  const consumed = items.reduce((s, i) => s + Number(i.consumed_quantity || 0), 0);

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>Inventory Center</h2>
          <p className="muted small">
            Site stock for general construction materials — receipts from procurement, issues to the
            works, and reorder alerts.
          </p>
        </div>
        <button type="button" className="button compact" disabled={busy} onClick={load}>
          Refresh
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      <div className="center-summary">
        <div className="hint">
          <b>Materials</b>
          <span> · {items.length}</span>
        </div>
        <div className="hint">
          <b>Received</b>
          <span> · {received.toLocaleString()}</span>
        </div>
        <div className="hint">
          <b>Consumed</b>
          <span> · {consumed.toLocaleString()}</span>
        </div>
        <div className="hint">
          <b>Reorder alerts</b>
          <span> · {insights.length}</span>
        </div>
      </div>

      {insights.length > 0 && (
        <div className="os-getting-started" style={{ marginTop: 8 }}>
          <h3>Reorder alerts</h3>
          <p>Materials at or below reorder level — review and restock before site works stall.</p>
          <ul className="os-steps" style={{ listStyle: "disc" }}>
            {insights.slice(0, 6).map((x) => (
              <li key={x.inventory_item_id}>
                <b>{x.material_name}</b> — available {x.available.toLocaleString()}, reorder at{" "}
                {x.reorder_level.toLocaleString()}{" "}
                <span className={"status status-" + (x.priority === "high" ? "rejected" : "proposed")}>
                  {x.priority}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {loading && !items.length ? (
        <p className="muted">Loading inventory…</p>
      ) : items.length === 0 ? (
        <div className="empty empty-card">
          <h3>No inventory items yet</h3>
          <p>
            When procurement lines are marked delivered, stock appears here automatically. You can
            then issue materials to site and set reorder levels.
          </p>
        </div>
      ) : (
        <>
          <div className="boq-toolbar row gap">
            <input
              type="search"
              aria-label="Search inventory"
              placeholder="Search material, code, location…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: 220, flex: 1 }}
            />
            <label style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
              <input
                type="checkbox"
                checked={lowOnly}
                onChange={(e) => setLowOnly(e.target.checked)}
              />
              <span style={{ fontSize: 12 }}>Low stock only</span>
            </label>
          </div>

          {filtered.length === 0 ? (
            <div className="empty empty-card">
              <h3>No matching materials</h3>
              <p>Try a different search or clear the low-stock filter.</p>
            </div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Material</th>
                    <th>Opening</th>
                    <th>Received</th>
                    <th>Consumed</th>
                    <th>Reserved</th>
                    <th>Available</th>
                    <th>Reorder</th>
                    <th>Location</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((i) => {
                    const available = availableQty(i);
                    return (
                      <tr key={i.id}>
                        <td>
                          <code className="boq-code">{i.item_code || "—"}</code>
                        </td>
                        <td>
                          <b>{i.material_name}</b>
                          <br />
                          <small className="muted">{i.specification || "No specification"}</small>
                        </td>
                        {editingId === i.id ? (
                          <>
                            <td>
                              <input
                                type="number"
                                min={0}
                                value={Number(edit.opening_quantity || 0)}
                                onChange={(e) =>
                                  setEdit({ ...edit, opening_quantity: Number(e.target.value) })
                                }
                                style={{ width: 70 }}
                              />
                            </td>
                            <td>{Number(i.received_quantity || 0).toLocaleString()}</td>
                            <td>
                              <input
                                type="number"
                                min={0}
                                value={Number(edit.consumed_quantity || 0)}
                                onChange={(e) =>
                                  setEdit({ ...edit, consumed_quantity: Number(e.target.value) })
                                }
                                style={{ width: 70 }}
                              />
                            </td>
                            <td>
                              <input
                                type="number"
                                min={0}
                                value={Number(edit.reserved_quantity || 0)}
                                onChange={(e) =>
                                  setEdit({ ...edit, reserved_quantity: Number(e.target.value) })
                                }
                                style={{ width: 70 }}
                              />
                            </td>
                            <td>
                              <b>{available.toLocaleString()}</b> {i.unit || ""}
                            </td>
                            <td>
                              <input
                                type="number"
                                min={0}
                                value={Number(edit.reorder_level || 0)}
                                onChange={(e) =>
                                  setEdit({ ...edit, reorder_level: Number(e.target.value) })
                                }
                                style={{ width: 70 }}
                              />
                            </td>
                            <td>
                              <input
                                value={edit.location || ""}
                                onChange={(e) => setEdit({ ...edit, location: e.target.value })}
                                style={{ width: 100 }}
                              />
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
                            <td>{Number(i.opening_quantity || 0).toLocaleString()}</td>
                            <td>{Number(i.received_quantity || 0).toLocaleString()}</td>
                            <td>{Number(i.consumed_quantity || 0).toLocaleString()}</td>
                            <td>{Number(i.reserved_quantity || 0).toLocaleString()}</td>
                            <td>
                              <b>{available.toLocaleString()}</b> {i.unit || ""}
                            </td>
                            <td>{Number(i.reorder_level || 0).toLocaleString()}</td>
                            <td>{i.location || "—"}</td>
                            <td>
                              <div className="row gap">
                                <button
                                  type="button"
                                  className="button compact"
                                  disabled={busy}
                                  onClick={() => {
                                    setEditingId(i.id);
                                    setEdit({ ...i });
                                  }}
                                >
                                  Update
                                </button>
                                <button
                                  type="button"
                                  className="button compact"
                                  disabled={busy || available <= 0}
                                  onClick={() => issue(i)}
                                >
                                  Issue
                                </button>
                              </div>
                            </td>
                          </>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
