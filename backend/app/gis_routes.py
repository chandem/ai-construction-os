"""Authenticated GIS read endpoints for project locations and infrastructure assets."""

from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .gis import gis_summary
from .routes import _project_for_member, _authenticated_client

router = APIRouter(prefix="/api/v1")


@router.get("/projects/{project_id}/gis/assets")
def list_gis_assets(project_id: str, token: str = Depends(get_access_token)):
    """List infrastructure assets for a project after checking organization membership."""
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
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
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    try:
        locations_result = (
            client.table("gis_locations")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        assets_result = (
            client.table("infrastructure_assets")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return {
            "data": gis_summary(
                locations_result.data or [],
                assets_result.data or [],
            )
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not load GIS summary. Verify the GIS tables and backend database access.",
        ) from exc
