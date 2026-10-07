"""Shared Gemini client helpers (chat, JSON, vision, embeddings)."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, TypeVar

from .config import settings

T = TypeVar("T")

# Transient capacity / rate-limit / upstream gateway errors from Gemini/Google APIs.
_RETRY_MARKERS = (
    "503",
    "502",
    "bad gateway",
    "UNAVAILABLE",
    "high demand",
    "429",
    "RESOURCE_EXHAUSTED",
    "rate limit",
    "quota",
    "try again",
)
_MAX_RETRIES = 4
_RETRY_DELAYS = (1.5, 3.0, 6.0, 12.0)


def _require_key() -> str:
    key = settings.ai_api_key
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return key


def get_client():
    from google import genai

    return genai.Client(api_key=_require_key())


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(m.lower() in msg for m in _RETRY_MARKERS)


def _with_retry(operation: Callable[[], T], *, label: str = "Gemini request") -> T:
    last: BaseException | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return operation()
        except Exception as exc:
            last = exc
            if not _is_transient(exc) or attempt == _MAX_RETRIES - 1:
                raise
            delay = _RETRY_DELAYS[min(attempt, len(_RETRY_DELAYS) - 1)]
            time.sleep(delay)
    assert last is not None
    raise last


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    try:
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            content = getattr(candidates[0], "content", None)
            parts = getattr(content, "parts", None) or []
            chunks = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
            if chunks:
                return "\n".join(chunks)
    except Exception:
        pass
    return ""


def generate_text(
    *,
    system: str,
    user: str,
    temperature: float = 0.2,
    model: str | None = None,
) -> str:
    client = get_client()
    model_id = model or settings.resolved_chat_model

    def _call_chat() -> Any:
        try:
            from google.genai import types

            chat = client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                ),
            )
            response = chat.send_message(user)
            return response
        except Exception:
            # Fallback for older or differently configured google-genai releases.
            return client.models.generate_content(
                model=model_id,
                contents=f"{system}\n\n---\n\n{user}",
                config={
                    "system_instruction": system,
                    "temperature": temperature,
                },
            )

    response = _with_retry(_call_chat, label="generate_text")
    return _extract_text(response).strip()


def generate_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.0,
    model: str | None = None,
) -> dict[str, Any]:
    client = get_client()
    model_id = model or settings.resolved_chat_model
    prompt = user + "\n\nRespond with valid JSON only. No markdown fences."

    def _call_json() -> Any:
        try:
            from google.genai import types

            chat = client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            return chat.send_message(prompt)
        except Exception:
            return client.models.generate_content(
                model=model_id,
                contents=f"{system}\n\n{prompt}",
                config={
                    "system_instruction": system,
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )

    response = _with_retry(_call_json, label="generate_json")
    raw = _extract_text(response).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {"data": data}


def generate_vision_json(
    *,
    system: str,
    prompt: str,
    image_bytes: bytes,
    mime_type: str = "image/png",
    temperature: float = 0.0,
    model: str | None = None,
) -> dict[str, Any]:
    from google.genai import types

    client = get_client()
    model_id = model or settings.resolved_chat_model
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt + "\n\nRespond with valid JSON only.",
    ]

    def _call_vision() -> Any:
        try:
            chat = client.chats.create(
                model=model_id,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                    response_mime_type="application/json",
                ),
            )
            return chat.send_message(contents)
        except Exception:
            return client.models.generate_content(
                model=model_id,
                contents=contents,
                config={
                    "system_instruction": system,
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )

    response = _with_retry(_call_vision, label="generate_vision_json")
    raw = _extract_text(response).strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {"data": data}


def embed_texts_gemini(texts: list[str]) -> list[list[float]]:
    """Embed texts with Gemini; returns vectors in input order."""
    if not texts:
        return []
    client = get_client()
    model_id = settings.gemini_embedding_model
    out: list[list[float]] = []
    batch_size = 16
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        batch_vecs: list[list[float]] = []
        for text in batch:

            def _call(t: str = text) -> Any:
                # The production pgvector column is vector(1536). Gemini embedding
                # models default to 3072 dimensions, so request a compatible
                # 1536-dimensional representation explicitly.
                from google.genai import types

                return client.models.embed_content(
                    model=model_id,
                    contents=t,
                    config=types.EmbedContentConfig(output_dimensionality=1536),
                )

            result = _with_retry(_call, label="embed_content")
            values = None
            embeddings = getattr(result, "embeddings", None)
            if embeddings and len(embeddings) > 0:
                emb = embeddings[0]
                values = getattr(emb, "values", None) or getattr(emb, "embedding", None)
            if values is None:
                values = getattr(result, "values", None)
            if values is None and hasattr(result, "embedding"):
                values = getattr(result.embedding, "values", None) or result.embedding
            batch_vecs.append(list(values) if values is not None else [])
        out.extend(batch_vecs)
    while len(out) < len(texts):
        out.append([])
    return out[: len(texts)]
