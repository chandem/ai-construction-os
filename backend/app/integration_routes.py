"""Authenticated integration read endpoints for connector catalog and sync status."""

from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token, get_current_user
from .integrations import list_connector_catalog, integrations_summary
from .routes import _authenticated_client, _project_for_member

router = APIRouter(prefix="/api/v1")


def _project_client(project_id: str, token: str):
    user = get_current_user(token)
    client = _authenticated_client(token)
    _project_for_member(project_id, user["id"], client)
    return client


@router.get("/projects/{project_id}/integrations/connectors")
def list_project_connectors(project_id: str, token: str = Depends(get_access_token)):
    """Return supported connector catalog and configured connections for a project."""
    client = _project_client(project_id, token)
    try:
        result = (
            client.table("integration_connections")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .execute()
        )
        return {
            "data": list_connector_catalog(),
            "connections": result.data or [],
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not load integration connectors. Verify integration_connections exists and backend database access.",
        ) from exc


@router.get("/projects/{project_id}/integrations/summary")
def get_project_integrations_summary(
    project_id: str, token: str = Depends(get_access_token)
):
    """Return project integration connection and sync-job counts."""
    client = _project_client(project_id, token)
    try:
        connections_result = (
            client.table("integration_connections")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        jobs_result = (
            client.table("integration_sync_jobs")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )
        return {
            "data": integrations_summary(
                connections_result.data or [],
                jobs_result.data or [],
            )
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not load integration summary. Verify integration tables exist and backend database access.",
        ) from exc
}
