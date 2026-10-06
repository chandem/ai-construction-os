"""Gemini-powered construction tool-calling agent."""
from __future__ import annotations

import json

from google import genai
from google.genai import types
from supabase import Client

from .config import settings
from .construction_tools import (
    calculate_concrete_volume,
    calculate_material_balance,
    calculate_project_progress,
)
from .project_data import (
    make_document_search_tool,
    make_project_priorities_tool,
    make_project_summary_tool,
)

CONSTRUCTION_AGENT_SYSTEM = """You are the Construction AI Agent inside an AI-first Construction OS.

The user message includes UPLOADED DOCUMENT CONTEXT. Use that context first for questions about
uploaded files, drawings, specifications, contracts, reports, bills of quantities, or maintenance plans.
Quote the excerpts and cite the document name. If the context has files but no excerpts, say the files
are uploaded and repeat the note. Do not call this a system error unless the note says the lookup failed.

Use get_project_summary for current project status, activities, materials, equipment, costs, or risks.
Use get_project_priorities when the user asks what to focus on, what needs attention, recommended
next actions, or project priorities.
Use calculation tools for concrete volume, project progress percentage, and remaining material quantity.
You may also call search_uploaded_documents if the preloaded context is not enough.

Do not invent project-specific facts, quantities, dates, costs, or document contents.
If the available data is insufficient, say what is missing.
For engineering, safety, contractual, or financial decisions, calculations and excerpts do not
replace review by a qualified professional or the governing project documents.
"""

BASE_CONSTRUCTION_TOOLS = [
    calculate_concrete_volume,
    calculate_project_progress,
    calculate_material_balance,
]

_TRANSIENT_ERROR_MARKERS = (
    "429",
    "resource_exhausted",
    "rate_limit",
    "rate limit",
    "too_many_requests",
    "503",
    "service_unavailable",
    "temporarily unavailable",
    "temporarily overloaded",
    "overloaded",
    "unavailable",
    "deadline exceeded",
    "timeout",
)


def _is_transient_gemini_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_ERROR_MARKERS)


def _document_context(document_search_tool, message: str) -> str:
    try:
        found = document_search_tool(message)
    except Exception as exc:
        found = {"matches": [], "note": "Document lookup failed: %s" % exc}
    return json.dumps(found, default=str)[:8000]


def _generate_with_model(
    client: genai.Client,
    model_id: str,
    message: str,
    project_id: str,
    project_summary_tool,
    project_priorities_tool,
    document_search_tool,
):
    context = _document_context(document_search_tool, message)
    chat = client.chats.create(
        model=model_id,
        config=types.GenerateContentConfig(
            system_instruction=CONSTRUCTION_AGENT_SYSTEM,
            temperature=0.2,
            tools=[
                *BASE_CONSTRUCTION_TOOLS,
                project_summary_tool,
                project_priorities_tool,
                document_search_tool,
            ],
        ),
    )
    return chat.send_message(
        "AUTHORIZED PROJECT ID: %s\n\nUPLOADED DOCUMENT CONTEXT:\n%s\n\nUSER REQUEST:\n%s"
        % (project_id, context, message)
    )


def run_construction_agent(
    message: str,
    project_id: str,
    db: Client,
    model: str | None = None,
) -> str:
    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    client = genai.Client(api_key=settings.ai_api_key)
    model_id = model or settings.resolved_chat_model
    models_to_try = [model_id, *settings.resolved_chat_fallback_models]
    project_summary_tool = make_project_summary_tool(db, project_id)
    project_priorities_tool = make_project_priorities_tool(db, project_id)
    document_search_tool = make_document_search_tool(db, project_id)

    last_error: Exception | None = None

    for index, candidate_model in enumerate(models_to_try):
        try:
            response = _generate_with_model(
                client,
                candidate_model,
                message,
                project_id,
                project_summary_tool,
                project_priorities_tool,
                document_search_tool,
            )
            return (response.text or "").strip()
        except Exception as exc:
            last_error = exc
            is_last_model = index == len(models_to_try) - 1
            if is_last_model or not _is_transient_gemini_error(exc):
                raise

    if last_error is not None:
        raise last_error

    raise RuntimeError("No Gemini chat model is configured")
