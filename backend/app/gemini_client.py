"""Shared Gemini client helpers (chat, JSON, vision, embeddings)."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, TypeVar

from .config import settings

T = TypeVar("T")

# Transient capacity / rate-limit errors from Gemini free tier
_RETRY_MARKERS = (
    "503",
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

    def _call() -> Any:
        try:
            return client.models.generate_content(
                model=model_id,
                contents=user,
                config={
                    "system_instruction": system,
                    "temperature": temperature,
                },
            )
        except TypeError:
            return client.models.generate_content(
                model=model_id,
                contents=f"{system}\n\n---\n\n{user}",
            )

    response = _with_retry(_call, label="generate_text")
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

    def _call() -> Any:
        try:
            return client.models.generate_content(
                model=model_id,
                contents=prompt,
                config={
                    "system_instruction": system,
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )
        except Exception:
            return client.models.generate_content(
                model=model_id,
                contents=f"{system}\n\n{prompt}",
            )

    response = _with_retry(_call, label="generate_json")
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

    def _call() -> Any:
        try:
            return client.models.generate_content(
                model=model_id,
                contents=contents,
                config={
                    "system_instruction": system,
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                },
            )
        except Exception:
            return client.models.generate_content(
                model=model_id,
                contents=contents,
            )

    response = _with_retry(_call, label="generate_vision_json")
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
                return client.models.embed_content(
                    model=model_id,
                    contents=t,
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
