"""Server-side health checks for the AI Document Processing connector."""

import httpx
from fastapi import APIRouter, Depends, HTTPException

from .auth import get_access_token
from .config import settings
from .routes import _authenticated_client, _project_for_member

router = APIRouter(prefix="/api/v1")


@router.get("/projects/{project_id}/integrations/ai-documents/health")
def check_ai_document_processing_health(
    project_id: str,
    token: str = Depends(get_access_token),
):
    """Check the remote connector without exposing its shared token to the browser."""
    user_client = _authenticated_client(token)
    user = user_client.auth.get_user(token)
    user_id = getattr(getattr(user, "user", None), "id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session.")
    _project_for_member(project_id, user_id, user_client)

    base_url = (settings.ai_document_processing_base_url or "").strip().rstrip("/")
    shared_token = (settings.ai_document_processing_token or "").strip()
    if not base_url or not shared_token:
        raise HTTPException(
            status_code=503,
            detail="AI Document Processing integration is not configured on the backend.",
        )

    try:
        response = httpx.get(
            f"{base_url}/api/v1/integrations/health",
            headers={"X-Integration-Token": shared_token},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI Document Processing service could not be reached.",
        ) from exc

    if response.status_code == 401:
        raise HTTPException(
            status_code=502,
            detail="AI Document Processing rejected the integration credentials.",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="AI Document Processing health check failed.",
        )

    try:
        remote = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI Document Processing returned an invalid health response.",
        ) from exc

    if remote.get("status") != "ok" or remote.get("service") != "ai-document-processing":
        raise HTTPException(
            status_code=502,
            detail="AI Document Processing returned an unexpected health response.",
        )

    return {
        "status": "connected",
        "connector": "ai_documents",
        "service": "ai-document-processing",
        "capabilities": remote.get("capabilities", []),
    }
