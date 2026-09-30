"""Shared Gemini client helpers (chat, JSON, vision, embeddings)."""

from __future__ import annotations

import json
import re
from typing import Any

from .config import settings


def _require_key() -> str:
    key = settings.ai_api_key
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return key


def get_client():
    from google import genai

    return genai.Client(api_key=_require_key())


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    # Fallback for SDK shape differences
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
    """Text completion with optional system instruction."""
    client = get_client()
    model_id = model or settings.gemini_chat_model
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=user,
            config={
                "system_instruction": system,
                "temperature": temperature,
            },
        )
    except TypeError:
        # Older SDK without config kwargs
        response = client.models.generate_content(
            model=model_id,
            contents=f"{system}\n\n---\n\n{user}",
        )
    return _extract_text(response).strip()


def generate_json(
    *,
    system: str,
    user: str,
    temperature: float = 0.0,
    model: str | None = None,
) -> dict[str, Any]:
    """Ask Gemini for JSON and parse it."""
    client = get_client()
    model_id = model or settings.gemini_chat_model
    prompt = user + "\n\nRespond with valid JSON only. No markdown fences."
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={
                "system_instruction": system,
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        )
    except Exception:
        response = client.models.generate_content(
            model=model_id,
            contents=f"{system}\n\n{prompt}",
        )
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
    """Vision + JSON response for drawing pages."""
    from google.genai import types

    client = get_client()
    model_id = model or settings.gemini_chat_model
    contents = [
        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        prompt + "\n\nRespond with valid JSON only.",
    ]
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config={
                "system_instruction": system,
                "temperature": temperature,
                "response_mime_type": "application/json",
            },
        )
    except Exception:
        response = client.models.generate_content(
            model=model_id,
            contents=contents,
        )
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
    model_id = settings.embedding_model
    out: list[list[float]] = []
    # Small batches for free-tier rate limits
    batch_size = 16
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        try:
            result = client.models.embed_content(
                model=model_id,
                contents=batch,
            )
        except TypeError:
            result = client.models.embed_content(
                model=model_id,
                content=batch[0] if len(batch) == 1 else batch,
            )
        embeddings = getattr(result, "embeddings", None)
        if embeddings:
            for emb in embeddings:
                values = getattr(emb, "values", None) or getattr(emb, "embedding", None)
                if values is not None:
                    out.append(list(values))
                else:
                    out.append([])
        else:
            # Single embedding response shapes
            values = getattr(result, "values", None)
            if values is not None:
                out.append(list(values))
            else:
                for _ in batch:
                    out.append([])
    # Pad if API returned fewer vectors
    while len(out) < len(texts):
        out.append([])
    return out[: len(texts)]
