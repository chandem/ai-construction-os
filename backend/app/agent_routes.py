from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .ai_assistant import _get_project_for_user
from .auth import get_access_token, get_current_user
from .config import settings
from .construction_agent import run_construction_agent
from .db import supabase_admin

router = APIRouter(prefix="/api/v1")


class ConstructionAgentRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)


class ConstructionAgentResponse(BaseModel):
    answer: str


@router.post(
    "/projects/{project_id}/ai/agent",
    response_model=ConstructionAgentResponse,
)
def construction_agent(
    project_id: str,
    request: ConstructionAgentRequest,
    token: str = Depends(get_access_token),
):
    user = get_current_user(token)

    if not settings.ai_api_key:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured: GEMINI_API_KEY is missing",
        )

    if supabase_admin is None:
        raise HTTPException(
            status_code=500,
            detail="Server database client is not configured.",
        )

    _get_project_for_user(project_id, user["id"], supabase_admin)

    try:
        answer = run_construction_agent(request.message)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Construction agent failed: {exc}",
        ) from exc

    return ConstructionAgentResponse(answer=answer)
