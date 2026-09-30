from .config import settings
from .gemini_client import embed_texts_gemini


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts with Gemini (text-embedding-004 by default).

    Legacy OPENAI model names in EMBEDDING_MODEL are mapped automatically.
    Reprocess documents if you previously stored 1536-d OpenAI vectors.
    """
    if not texts:
        return []

    if not settings.ai_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    return embed_texts_gemini(texts)
