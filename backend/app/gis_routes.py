"""Authenticated GIS endpoints for project locations and infrastructure assets."""

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .gis import gis_summary
from .routes import _project_for_member, _authenticated_client

router = APIRouter(prefix="/api/v1")

ASSET_FIELDS = {
    "name", "asset_type", "geometry_type", "location_id", "latitude",
    "longitude", "work_section", "design_asset_id", "description", "status",
    "properties",
}
ASSET_TYPES = {
    "building", "road", "bridge", "culvert", "utility", "pipeline",
    "tower", "equipment", "boundary", "other",
}
GEOMETRY_TYPES = {"point", "line", "polygon", "unknown"}
ASSET_STATUSES = {"planned", "under_construction", "existing", "demolished", "archived"}


def _context(project_id: str, token: str):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    return client


def _clean_asset(payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    row = {key: value for key, value in payload.items() if key in ASSET_FIELDS}
    if not partial and not str(row.get("name") or "").strip():
        raise HTTPException(status_code=422, detail="Asset name is required.")
    if "name" in row:
        row["name"] = str(row["name"]).strip()
        if not row["name"]:
            raise HTTPException(status_code=422, detail="Asset name is required.")
    if "asset_type" in row and row["asset_type"] not in ASSET_TYPES:
        raise HTTPException(status_code=422, detail="Invalid asset type.")
    if "geometry_type" in row and row["geometry_type"] not in GEOMETRY_TYPES:
        raise HTTPException(status_code=422, detail="Invalid geometry type.")
    if "status" in row and row["status"] not in ASSET_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid asset status.")
    for key in ("latitude", "longitude"):
        if key in row and row[key] not in (None, ""):
            try:
                row[key] = float(row[key])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=f"{key} must be a number.") from exc
            low, high = (-90, 90) if key == "latitude" else (-180, 180)
            if not low <= row[key] <= high:
                raise HTTPException(status_code=422, detail=f"{key} must be between {low} and {high}.")
        elif key in row:
            row[key] = None
    return row


@router.get("/projects/{project_id}/gis/assets")
def list_gis_assets(project_id: str, token: str = Depends(get_access_token)):
    """List infrastructure assets for a project after checking organization membership."""
    client = _context(project_id, token)
    try:
        result = (
            client.table("infrastructure_assets")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {"data": result.data or []}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not load GIS assets. Verify the infrastructure_assets table and backend database access.",
        ) from exc


@router.get("/projects/{project_id}/gis/summary")
def get_gis_summary(project_id: str, token: str = Depends(get_access_token)):
    """Return GIS counts for the selected project."""
    client = _context(project_id, token)
    try:
        locations_result = client.table("gis_locations").select("*").eq("project_id", project_id).execute()
        assets_result = client.table("infrastructure_assets").select("*").eq("project_id", project_id).execute()
        return {"data": gis_summary(locations_result.data or [], assets_result.data or [])}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not load GIS summary. Verify the GIS tables and backend database access.",
        ) from exc


@router.post("/projects/{project_id}/gis/assets", status_code=201)
def create_gis_asset(
    project_id: str,
    payload: dict[str, Any] = Body(...),
    token: str = Depends(get_access_token),
):
    """Create a project infrastructure asset after membership and input validation."""
    client = _context(project_id, token)
    row = _clean_asset(payload)
    row.update({"project_id": project_id, "source": "gis_ops"})
    try:
        result = client.table("infrastructure_assets").insert(row).execute()
        if not result.data:
            raise HTTPException(status_code=502, detail="The GIS asset was not saved.")
        return {"data": result.data[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not save GIS asset.") from exc


@router.patch("/projects/{project_id}/gis/assets/{asset_id}")
def update_gis_asset(
    project_id: str,
    asset_id: str,
    payload: dict[str, Any] = Body(...),
    token: str = Depends(get_access_token),
):
    """Update editable fields on a GIS asset scoped to the selected project."""
    client = _context(project_id, token)
    row = _clean_asset(payload, partial=True)
    if not row:
        raise HTTPException(status_code=422, detail="Provide at least one editable field.")
    try:
        result = (
            client.table("infrastructure_assets").update(row)
            .eq("project_id", project_id).eq("id", asset_id).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="GIS asset not found.")
        return {"data": result.data[0]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not update GIS asset.") from exc


@router.delete("/projects/{project_id}/gis/assets/{asset_id}", status_code=204)
def delete_gis_asset(project_id: str, asset_id: str, token: str = Depends(get_access_token)):
    """Delete a GIS asset scoped to the selected project."""
    client = _context(project_id, token)
    try:
        result = (
            client.table("infrastructure_assets").delete()
            .eq("project_id", project_id).eq("id", asset_id).execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="GIS asset not found.")
        return None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not delete GIS asset.") from exc
