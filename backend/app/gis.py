"""GIS foundation: project locations and infrastructure assets.

Chain: project → locations (sites/zones) → infrastructure assets (point/line/area).
Coordinates are WGS84 lat/lng for MVP; no external map API required for the data model.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

GIS_SOURCE = "gis_ops"

LOCATION_TYPES = ("site", "zone", "compound", "access", "yard", "other")
LOCATION_STATUSES = ("proposed", "active", "inactive", "archived")

ASSET_TYPES = (
    "building",
    "road",
    "bridge",
    "culvert",
    "utility",
    "pipeline",
    "tower",
    "equipment",
    "boundary",
    "other",
)
ASSET_GEOM = ("point", "line", "polygon", "unknown")
ASSET_STATUSES = ("planned", "under_construction", "existing", "demolished", "archived")


def build_location(
    *,
    project_id: str,
    name: str,
    location_type: str = "site",
    latitude: float | None = None,
    longitude: float | None = None,
    address: str | None = None,
    description: str | None = None,
    parent_location_id: str | None = None,
    status: str = "active",
) -> dict[str, Any]:
    if location_type not in LOCATION_TYPES:
        location_type = "other"
    if status not in LOCATION_STATUSES:
        status = "active"
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "name": name or "Location",
        "location_type": location_type,
        "latitude": latitude,
        "longitude": longitude,
        "address": address or "",
        "description": description or "",
        "parent_location_id": parent_location_id,
        "status": status,
        "source": GIS_SOURCE,
        "properties": {},
    }


def build_infrastructure_asset(
    *,
    project_id: str,
    name: str,
    asset_type: str = "building",
    geometry_type: str = "point",
    location_id: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    work_section: str | None = None,
    design_asset_id: str | None = None,
    description: str | None = None,
    status: str = "planned",
) -> dict[str, Any]:
    if asset_type not in ASSET_TYPES:
        asset_type = "other"
    if geometry_type not in ASSET_GEOM:
        geometry_type = "unknown"
    if status not in ASSET_STATUSES:
        status = "planned"
    return {
        "id": str(uuid4()),
        "project_id": project_id,
        "asset_code": f"AST-{str(uuid4())[:8].upper()}",
        "name": name or "Asset",
        "asset_type": asset_type,
        "geometry_type": geometry_type,
        "location_id": location_id,
        "latitude": latitude,
        "longitude": longitude,
        "work_section": work_section,
        "design_asset_id": design_asset_id,
        "description": description or "",
        "status": status,
        "source": GIS_SOURCE,
        "properties": {},
    }


def assets_from_engineering_elements(
    elements: list[dict[str, Any]],
    *,
    project_id: str,
    location_id: str | None = None,
) -> list[dict[str, Any]]:
    """Propose infrastructure assets from engineering elements (name/type only)."""
    assets: list[dict[str, Any]] = []
    for el in elements:
        et = str(el.get("element_type") or "other").lower()
        name = el.get("name") or el.get("identifier") or et
        geom = "point"
        if et in ("road", "pipe", "drainage"):
            geom = "line"
        elif et in ("slab", "room", "pavement"):
            geom = "polygon"
        assets.append(
            build_infrastructure_asset(
                project_id=project_id,
                name=str(name),
                asset_type=_map_element_to_asset_type(et),
                geometry_type=geom,
                location_id=location_id,
                work_section=el.get("work_section") if isinstance(el.get("work_section"), str) else None,
                design_asset_id=el.get("design_asset_id"),
                description=el.get("location_description") or "",
                status="planned",
            )
        )
    return assets


def _map_element_to_asset_type(et: str) -> str:
    mapping = {
        "foundation": "building",
        "footing": "building",
        "column": "building",
        "beam": "building",
        "slab": "building",
        "wall": "building",
        "retaining_wall": "building",
        "stair": "building",
        "road": "road",
        "pavement": "road",
        "culvert": "culvert",
        "pipe": "pipeline",
        "drainage": "utility",
        "equipment": "equipment",
    }
    return mapping.get(et, "other")


def gis_summary(
    locations: list[dict[str, Any]],
    assets: list[dict[str, Any]],
) -> dict[str, Any]:
    loc_by_type: dict[str, int] = {}
    for loc in locations:
        t = loc.get("location_type") or "other"
        loc_by_type[t] = loc_by_type.get(t, 0) + 1
    asset_by_type: dict[str, int] = {}
    geocoded = 0
    for a in assets:
        t = a.get("asset_type") or "other"
        asset_by_type[t] = asset_by_type.get(t, 0) + 1
        if a.get("latitude") is not None and a.get("longitude") is not None:
            geocoded += 1
    loc_geocoded = sum(
        1 for loc in locations if loc.get("latitude") is not None and loc.get("longitude") is not None
    )
    return {
        "location_count": len(locations),
        "locations_by_type": loc_by_type,
        "locations_geocoded": loc_geocoded,
        "asset_count": len(assets),
        "assets_by_type": asset_by_type,
        "assets_geocoded": geocoded,
        "notes": "GIS locations and assets use WGS84 lat/lng. Map rendering is a later UI step.",
    }


def persist_location(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "name": row.get("name"),
        "location_type": row.get("location_type"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "address": row.get("address"),
        "description": row.get("description"),
        "parent_location_id": row.get("parent_location_id"),
        "status": row.get("status") or "active",
        "source": row.get("source") or GIS_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("gis_locations").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_asset(client, row: dict[str, Any]) -> dict[str, Any] | None:
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "asset_code": row.get("asset_code"),
        "name": row.get("name"),
        "asset_type": row.get("asset_type"),
        "geometry_type": row.get("geometry_type"),
        "location_id": row.get("location_id"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "work_section": row.get("work_section"),
        "design_asset_id": row.get("design_asset_id"),
        "description": row.get("description"),
        "status": row.get("status") or "planned",
        "source": row.get("source") or GIS_SOURCE,
        "properties": row.get("properties") or {},
    }
    try:
        client.table("infrastructure_assets").upsert(payload).execute()
        return payload
    except Exception:
        return None


def persist_assets_batch(client, assets: list[dict[str, Any]]) -> int:
    if not assets:
        return 0
    n = 0
    for a in assets:
        if persist_asset(client, a) is not None:
            n += 1
    return n
