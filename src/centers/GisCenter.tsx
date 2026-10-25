import React from "react";
import { apiDelete, apiGet, apiPatch, apiPost } from "../api";

type Props = { projectId: string; token: string };
type Asset = {
  id: string;
  asset_code?: string | null;
  name: string;
  asset_type?: string | null;
  geometry_type?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  work_section?: string | null;
  description?: string | null;
  status?: string | null;
  created_at?: string;
};

const ASSET_TYPES = ["building", "road", "bridge", "culvert", "utility", "pipeline", "tower", "equipment", "boundary", "other"];
const STATUSES = [
  ["planned", "Planned"],
  ["under_construction", "Under construction"],
  ["existing", "Existing"],
  ["demolished", "Demolished"],
  ["archived", "Archived"],
];

function coordinate(value: number | null | undefined) {
  return value == null || !Number.isFinite(Number(value)) ? "—" : Number(value).toFixed(6);
}

function mapUrl(asset: Asset) {
  if (asset.latitude == null || asset.longitude == null) return "";
  const lat = Number(asset.latitude);
  const lon = Number(asset.longitude);
  const delta = 0.015;
  const bbox = [lon - delta, lat - delta, lon + delta, lat + delta].join("%2C");
  return `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lon}`;
}

export function GisCenter({ projectId, token }: Props) {
  const [assets, setAssets] = React.useState<Asset[]>([]);
  const [summary, setSummary] = React.useState<Record<string, any>>({});
  const [selectedId, setSelectedId] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("all");
  const [busy, setBusy] = React.useState(false);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [notice, setNotice] = React.useState("");
  const [formOpen, setFormOpen] = React.useState(false);
  const [editingId, setEditingId] = React.useState("");
  const [name, setName] = React.useState("");
  const [assetType, setAssetType] = React.useState("road");
  const [geometryType, setGeometryType] = React.useState("point");
  const [latitude, setLatitude] = React.useState("");
  const [longitude, setLongitude] = React.useState("");
  const [workSection, setWorkSection] = React.useState("");
  const [status, setStatus] = React.useState("existing");
  const [description, setDescription] = React.useState("");

  const load = React.useCallback(async () => {
    if (!projectId || !token) return;
    setLoading(true);
    setError("");
    try {
      const [assetResponse, summaryResponse] = await Promise.all([
        apiGet(`/api/v1/projects/${projectId}/gis/assets`, token),
        apiGet(`/api/v1/projects/${projectId}/gis/summary`, token),
      ]);
      const rows: Asset[] = Array.isArray(assetResponse?.data) ? assetResponse.data : [];
      setAssets(rows);
      setSummary(summaryResponse?.data || {});
      setSelectedId((current) => rows.some((row) => row.id === current) ? current : rows[0]?.id || "");
    } catch (e: any) {
      setError(e?.message || "Could not load GIS data.");
    } finally {
      setLoading(false);
    }
  }, [projectId, token]);

  React.useEffect(() => { void load(); }, [load]);

  const filteredAssets = assets.filter((asset) => {
    const q = search.trim().toLowerCase();
    const matchesSearch = !q || [asset.name, asset.asset_code, asset.asset_type, asset.work_section, asset.description]
      .some((value) => String(value || "").toLowerCase().includes(q));
    return matchesSearch && (statusFilter === "all" || asset.status === statusFilter);
  });
  const selected = assets.find((asset) => asset.id === selectedId) || null;
  const geocoded = assets.filter((asset) => asset.latitude != null && asset.longitude != null).length;

  function resetForm() {
    setEditingId("");
    setName("");
    setAssetType("road");
    setGeometryType("point");
    setLatitude("");
    setLongitude("");
    setWorkSection("");
    setStatus("existing");
    setDescription("");
  }

  function startEdit(asset: Asset) {
    setEditingId(asset.id);
    setName(asset.name || "");
    setAssetType(asset.asset_type || "other");
    setGeometryType(asset.geometry_type || "point");
    setLatitude(asset.latitude == null ? "" : String(asset.latitude));
    setLongitude(asset.longitude == null ? "" : String(asset.longitude));
    setWorkSection(asset.work_section || "");
    setStatus(asset.status || "planned");
    setDescription(asset.description || "");
    setFormOpen(true);
    setError("");
    setNotice("");
  }

  async function saveAsset(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      setError("Enter an asset name.");
      return;
    }
    const lat = latitude.trim() ? Number(latitude) : null;
    const lon = longitude.trim() ? Number(longitude) : null;
    if ((lat !== null && (!Number.isFinite(lat) || lat < -90 || lat > 90)) ||
        (lon !== null && (!Number.isFinite(lon) || lon < -180 || lon > 180))) {
      setError("Latitude must be −90 to 90 and longitude −180 to 180.");
      return;
    }
    if ((lat === null) !== (lon === null)) {
      setError("Enter both latitude and longitude, or leave both blank.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    const payload = {
      name: name.trim(), asset_type: assetType, geometry_type: geometryType,
      latitude: lat, longitude: lon, work_section: workSection.trim() || null,
      status, description: description.trim() || null,
    };
    try {
      const path = `/api/v1/projects/${projectId}/gis/assets`;
      const response = editingId
        ? await apiPatch(`${path}/${editingId}`, token, payload)
        : await apiPost(path, token, payload);
      const saved: Asset | undefined = response?.data;
      setNotice(editingId ? "GIS asset updated." : "GIS asset added.");
      setFormOpen(false);
      resetForm();
      await load();
      if (saved?.id) setSelectedId(saved.id);
    } catch (e: any) {
      setError(e?.message || "Could not save GIS asset.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteAsset(asset: Asset) {
    if (!window.confirm(`Delete "${asset.name}" from this project?`)) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await apiDelete(`/api/v1/projects/${projectId}/gis/assets/${asset.id}`, token);
      setNotice("GIS asset deleted.");
      if (selectedId === asset.id) setSelectedId("");
      await load();
    } catch (e: any) {
      setError(e?.message || "Could not delete GIS asset.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel gis-center">
      <div className="panel-head">
        <div>
          <h2>GIS &amp; Infrastructure</h2>
          <p className="muted small">Map project assets, track coordinates, and manage infrastructure records.</p>
        </div>
        <div className="row gap">
          <button type="button" className="button compact" disabled={busy || loading} onClick={() => void load()}>Refresh</button>
          <button type="button" className="button primary compact" disabled={busy} onClick={() => { resetForm(); setFormOpen((value) => !value); }}>
            {formOpen && !editingId ? "Close form" : "Add asset"}
          </button>
        </div>
      </div>

      {error && <div className="error" role="alert">{error}</div>}
      {notice && <div className="success" role="status">{notice}</div>}

      <div className="center-summary">
        <div className="hint"><b>Infrastructure assets</b><span> · {summary.asset_count ?? assets.length}</span></div>
        <div className="hint"><b>Mapped coordinates</b><span> · {summary.assets_geocoded ?? geocoded}</span></div>
        <div className="hint"><b>Project locations</b><span> · {summary.location_count ?? 0}</span></div>
        <div className="hint"><b>Need coordinates</b><span> · {assets.length - geocoded}</span></div>
      </div>

      {formOpen && (
        <form className="panel" onSubmit={saveAsset} style={{ marginTop: 16 }}>
          <div className="panel-head">
            <div>
              <h3>{editingId ? "Edit infrastructure asset" : "Add infrastructure asset"}</h3>
              <p className="muted small">Coordinates use WGS84 decimal degrees. Leave both coordinates blank if not yet surveyed.</p>
            </div>
          </div>
          <div className="form-grid">
            <label>Asset name *<input required value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Shakiso access road" /></label>
            <label>Asset type<select value={assetType} onChange={(e) => setAssetType(e.target.value)}>{ASSET_TYPES.map((type) => <option key={type} value={type}>{type.replaceAll("_", " ")}</option>)}</select></label>
            <label>Geometry<select value={geometryType} onChange={(e) => setGeometryType(e.target.value)}><option value="point">Point</option><option value="line">Line</option><option value="polygon">Polygon</option><option value="unknown">Unknown</option></select></label>
            <label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}>{STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Latitude<input inputMode="decimal" type="number" min="-90" max="90" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} placeholder="e.g. 5.950000" /></label>
            <label>Longitude<input inputMode="decimal" type="number" min="-180" max="180" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} placeholder="e.g. 38.980000" /></label>
            <label>Work section / chainage<input value={workSection} onChange={(e) => setWorkSection(e.target.value)} placeholder="e.g. km 12+500 – km 13+000" /></label>
            <label>Description<input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Condition, location notes, or identifier" /></label>
          </div>
          <div className="row gap" style={{ marginTop: 12 }}>
            <button type="submit" className="button primary compact" disabled={busy}>{busy ? "Saving…" : editingId ? "Save changes" : "Create asset"}</button>
            <button type="button" className="button compact" disabled={busy} onClick={() => { setFormOpen(false); resetForm(); }}>Cancel</button>
          </div>
        </form>
      )}

      <div className="gis-layout" style={{ marginTop: 16 }}>
        <div className="gis-map-panel">
          <div className="panel-head">
            <div><h3>Project map</h3><p className="muted small">{selected?.name || "Select a geocoded asset from the register"}</p></div>
            {selected && selected.latitude != null && selected.longitude != null &&
              <a className="button compact" href={`https://www.openstreetmap.org/?mlat=${selected.latitude}&mlon=${selected.longitude}#map=15/${selected.latitude}/${selected.longitude}`} target="_blank" rel="noreferrer">Open full map ↗</a>}
          </div>
          {selected && mapUrl(selected) ? (
            <iframe title={`Map location for ${selected.name}`} src={mapUrl(selected)} loading="lazy" referrerPolicy="no-referrer-when-downgrade" />
          ) : (
            <div className="gis-map-empty">
              <div aria-hidden="true" style={{ fontSize: 32 }}>⌖</div>
              <h3>No mapped asset selected</h3>
              <p className="muted small">Add latitude and longitude to an asset, or select an asset that already has coordinates.</p>
            </div>
          )}
          <p className="muted small">Map tiles © OpenStreetMap contributors. Locations are only shown when coordinates are supplied.</p>
        </div>

        <div className="gis-register">
          <div className="panel-head"><h3>Asset register</h3><span className="muted small">{filteredAssets.length} shown</span></div>
          <div className="row gap" style={{ marginBottom: 10 }}>
            <input aria-label="Search GIS assets" type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, type, section…" style={{ minWidth: 0, flex: 1 }} />
            <select aria-label="Filter assets by status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}><option value="all">All statuses</option>{STATUSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
          </div>
          {loading ? <p className="muted">Loading GIS assets…</p> : filteredAssets.length === 0 ? (
            <div className="empty empty-card"><h3>{assets.length ? "No matching assets" : "No GIS assets yet"}</h3><p>{assets.length ? "Change the search or status filter." : "Add an asset to start building the project GIS register."}</p></div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Asset</th><th>Type</th><th>Coordinates</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>{filteredAssets.map((asset) => (
                  <tr key={asset.id} style={selectedId === asset.id ? { outline: "1px solid var(--accent, #64748b)" } : undefined}>
                    <td><button type="button" className="button compact" onClick={() => setSelectedId(asset.id)}>{asset.name}</button><div className="muted small">{asset.asset_code || asset.work_section || "No code / section"}</div></td>
                    <td>{String(asset.asset_type || "other").replaceAll("_", " ")}</td>
                    <td>{coordinate(asset.latitude)}, {coordinate(asset.longitude)}</td>
                    <td>{String(asset.status || "planned").replaceAll("_", " ")}</td>
                    <td><div className="row gap"><button type="button" className="button compact" disabled={busy} onClick={() => startEdit(asset)}>Edit</button><button type="button" className="button compact" disabled={busy} onClick={() => void deleteAsset(asset)}>Delete</button></div></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
