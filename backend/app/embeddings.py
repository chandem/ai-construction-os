from .config import settings
from .gemini_client import embed_texts_gemini


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, preserving input order (Gemini).

    Returns an empty list when *texts* is empty so callers can skip
    knowledge-chunk inserts without raising.

    Note: Gemini text-embedding-004 is typically 768 dimensions.
    If you previously used OpenAI (1536-d), re-upload/reprocess documents
    so pgvector matches the new dimension.
    """
    if not texts:
        return []

    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    return embed_texts_gemini(texts)
