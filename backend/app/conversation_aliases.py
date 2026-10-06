"""Compatibility paths used by the current frontend.

The UI calls /conversations; the assistant router exposes /ai/conversations.
"""

from fastapi import APIRouter, Depends

from .ai_assistant import list_conversations, list_messages
from .auth import get_access_token

router = APIRouter(prefix="/api/v1")


@router.get("/projects/{project_id}/conversations")
def list_conversations_compat(project_id: str, token: str = Depends(get_access_token)):
    return list_conversations(project_id, token)


@router.get("/conversations/{conversation_id}/messages")
def list_messages_compat(conversation_id: str, token: str = Depends(get_access_token)):
    return list_messages(conversation_id, token)
