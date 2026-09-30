import time
from typing import Any, Callable, TypeVar

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

from .auth import get_access_token, get_current_user
from .config import settings
from .db import supabase
from .embeddings import embed_texts

router = APIRouter(prefix="/api/v1")

AI_MODEL = "gpt-4.1-mini"
MAX_HISTORY = 10
MAX_SOURCES = 8
MIN_SIMILARITY = 0.35
DEFAULT_TITLE = "Construction AI Assistant"
TITLE_MAX_LEN = 72
DB_RETRIES = 3
DB_RETRY_DELAYS = (0.25, 0.75)

T = TypeVar("T")


def _authenticated_client(token: str) -> Client:
    client = create_client(
        settings.supabase_url,
        settings.supabase_key,
        options=ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
            postgrest_client_timeout=15,
        ),
    )
    client.postgrest.auth(token)
    return client


def _db_execute(operation: Callable[[], T], operation_name: str) -> T:
    for attempt in range(DB_RETRIES):
        try:
            return operation()
        except (httpx.ReadError, httpx.ConnectError, httpx.TimeoutException, OSError) as exc:
            if attempt == DB_RETRIES - 1:
                raise HTTPException(
                    status_code=503,
                    detail=f"Database service temporarily unavailable while {operation_name}. Please retry.",
                ) from exc
            time.sleep(DB_RETRY_DELAYS[attempt])
    raise RuntimeError("Unreachable")

SYSTEM_PROMPT = """You are the Construction AI Assistant inside an AI-first Construction OS.

Your job is to help authorized construction professionals understand project information,
documents, schedules, quantities, costs, contracts, quality, safety, procurement, materials,
equipment and site records.

GROUNDING RULES:
1. Treat supplied project evidence as the primary evidence for project-specific questions.
2. Never invent project facts, quantities, dates, contract terms, costs, or document contents.
3. If evidence is insufficient, clearly say so and explain what information is missing.
4. Distinguish documented facts from calculations, assumptions, and general construction knowledge.
5. When calculating, show the key inputs and formula briefly.
6. For engineering, contractual, financial, quality, or safety decisions, provide analysis but state when qualified human review or the governing project document/code is required.
7. Keep answers practical and concise. Use headings and bullets when useful.
8. Cite project evidence inline using [Source N] where N matches the supplied source list.
"""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12000)
    conversation_id: str | None = None


class SourceOut(BaseModel):
    document_id: str
    title: str | None = None
    page_number: int | None = None
    similarity: float | None = None
    citation: str


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceOut]
    title: str | None = None


def _title_from_message(message: str) -> str:
    cleaned = " ".join(message.strip().split())
    if not cleaned:
        return DEFAULT_TITLE
    if len(cleaned) <= TITLE_MAX_LEN:
        return cleaned
    return cleaned[: TITLE_MAX_LEN - 1].rstrip() + "…"


def _get_project_for_user(project_id: str, user_id: str, token: str) -> dict[str, Any]:
    client = supabase
    client.postgrest.auth(token)
    result = (
        client.table("projects")
        .select("id,organization_id,name,code")
        .eq("id", project_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    membership = (
        client.table("organization_members")
        .select("organization_id,role")
        .eq("organization_id", result.data["organization_id"])
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not membership.data:
        raise HTTPException(
            status_code=403, detail="You are not a member of this project organization"
        )
    return result.data


def _get_or_create_conversation(
    project_id: str, user_id: str, conversation_id: str | None, token: str, first_message: str
) -> dict[str, Any]:
    client = supabase
    client.postgrest.auth(token)
    if conversation_id:
        result = (
            client.table("ai_conversations")
            .select("id,project_id,user_id,title")
            .eq("id", conversation_id)
            .eq("project_id", project_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return result.data

    title = _title_from_message(first_message)
    result = (
        client.table("ai_conversations")
        .insert(
            {
                "project_id": project_id,
                "user_id": user_id,
                "title": title,
            }
        )
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Could not create conversation")
    return result.data[0]


def _maybe_update_title(conversation: dict[str, Any], message: str, token: str) -> str:
    """If the conversation still has the default title, rename it from the user message."""
    current = (conversation.get("title") or "").strip()
    if current and current != DEFAULT_TITLE:
        return current

    title = _title_from_message(message)
    client = supabase
    client.postgrest.auth(token)
    client.table("ai_conversations").update({"title": title}).eq(
        "id", conversation["id"]
    ).execute()
    conversation["title"] = title
    return title


def _history(conversation_id: str, token: str) -> list[dict[str, str]]:
    client = supabase
    client.postgrest.auth(token)
    result = (
        client.table("ai_messages")
        .select("role,content")
        .eq("conversation_id", conversation_id)
        .order("created_at", desc=True)
        .limit(MAX_HISTORY)
        .execute()
    )
    rows = list(reversed(result.data or []))
    return [
        {"role": row["role"], "content": row["content"]}
        for row in rows
        if row["role"] in {"user", "assistant"}
    ]


def _retrieve(project_id: str, question: str, token: str) -> list[dict[str, Any]]:
    embedding = embed_texts([question])[0]
    client = supabase
    client.postgrest.auth(token)
    result = client.rpc(
        "match_ai_knowledge_chunks",
        {
            "query_embedding": embedding,
            "match_project_id": project_id,
            "match_count": MAX_SOURCES,
        },
    ).execute()
    matches = result.data or []
    return [match for match in matches if (match.get("similarity") or 0) >= MIN_SIMILARITY]


def _document_titles(project_id: str, document_ids: list[str], token: str) -> dict[str, str]:
    if not document_ids:
        return {}
    client = supabase
    client.postgrest.auth(token)
    result = (
        client.table("documents")
        .select("id,name")
        .eq("project_id", project_id)
        .in_("id", document_ids)
        .execute()
    )
    return {str(row["id"]): row["name"] for row in (result.data or [])}


@router.post("/projects/{project_id}/ai/chat", response_model=ChatResponse)
def chat(project_id: str, request: ChatRequest, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503, detail="AI service is not configured: OPENAI_API_KEY is missing"
        )

    project = _get_project_for_user(project_id, user["id"], token)
    conversation = _get_or_create_conversation(
        project_id, user["id"], request.conversation_id, token, request.message
    )
    title = _maybe_update_title(conversation, request.message, token)

    try:
        matches = _retrieve(project_id, request.message, token)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge search failed: {exc}") from exc

    titles = _document_titles(
        project_id, [str(m.get("document_id")) for m in matches], token
    )
    context_parts = []
    sources: list[dict[str, Any]] = []

    for index, match in enumerate(matches, start=1):
        document_id = str(match.get("document_id"))
        doc_title = titles.get(document_id)
        page = match.get("page_number")
        similarity = match.get("similarity")
        citation = f"[Source {index}] {doc_title or document_id}"
        if page:
            citation += f", page {page}"

        context_parts.append(
            f"[Source {index}]\nDocument: {doc_title or document_id}\nPage: {page or 'N/A'}\n"
            f"Similarity: {similarity or 0:.4f}\nContent:\n{match.get('content', '')}"
        )
        sources.append(
            {
                "document_id": document_id,
                "title": doc_title,
                "page_number": page,
                "similarity": similarity,
                "citation": citation,
            }
        )

    context = (
        "\n\n".join(context_parts)
        if context_parts
        else "No sufficiently relevant project document evidence was found."
    )
    history = _history(conversation["id"], token)

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history,
        {
            "role": "user",
            "content": (
                f"Project: {project.get('name')} ({project.get('code') or 'no code'})\n\n"
                f"PROJECT EVIDENCE:\n{context}\n\nUSER QUESTION:\n{request.message}"
            ),
        },
    ]

    try:
        response = client.chat.completions.create(
            model=AI_MODEL, messages=messages, temperature=0.2
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI generation failed: {exc}") from exc

    answer = response.choices[0].message.content or "I could not generate an answer."
    usage = response.usage
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0

    db = supabase
    db.postgrest.auth(token)
    db.table("ai_messages").insert(
        {"conversation_id": conversation["id"], "role": "user", "content": request.message}
    ).execute()
    db.table("ai_messages").insert(
        {"conversation_id": conversation["id"], "role": "assistant", "content": answer}
    ).execute()

    if sources:
        db.table("ai_sources").insert(
            [
                {
                    "conversation_id": conversation["id"],
                    "document_id": source["document_id"],
                    "source_type": "ai_knowledge_chunk",
                    "title": source["title"],
                    "citation": source["citation"],
                    "metadata": {
                        "page_number": source["page_number"],
                        "similarity": source["similarity"],
                    },
                }
                for source in sources
            ]
        ).execute()

    db.table("ai_usage").insert(
        {
            "organization_id": project["organization_id"],
            "project_id": project_id,
            "user_id": user["id"],
            "provider": "openai",
            "model": AI_MODEL,
            "operation": "construction_ai_chat",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": 0,
        }
    ).execute()

    return {
        "conversation_id": conversation["id"],
        "answer": answer,
        "sources": sources,
        "title": title,
    }


@router.get("/projects/{project_id}/ai/conversations")
def list_conversations(project_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    _get_project_for_user(project_id, user["id"], token)
    client = supabase
    client.postgrest.auth(token)
    result = (
        client.table("ai_conversations")
        .select("id,project_id,user_id,title,created_at")
        .eq("project_id", project_id)
        .eq("user_id", user["id"])
        .order("created_at", desc=True)
        .execute()
    )
    return {"data": result.data or []}


@router.get("/ai/conversations/{conversation_id}/messages")
def list_messages(conversation_id: str, token: str = Depends(get_access_token)):
    user = get_current_user(token)
    client = supabase
    client.postgrest.auth(token)
    conversation = (
        client.table("ai_conversations")
        .select("id,project_id,user_id")
        .eq("id", conversation_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not conversation.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _get_project_for_user(conversation.data["project_id"], user["id"], token)
    result = (
        client.table("ai_messages")
        .select("id,role,content,created_at")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return {"data": result.data or []}
