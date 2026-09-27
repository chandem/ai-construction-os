from openai import OpenAI

from .config import settings

# OpenAI embedding endpoints accept large batches; keep a safe ceiling.
_BATCH_SIZE = 64


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts, preserving input order.

    Returns an empty list when *texts* is empty so callers can skip
    knowledge-chunk inserts without raising.
    """
    if not texts:
        return []

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key)
    embeddings: list[list[float]] = []

    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start : start + _BATCH_SIZE]
        response = client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        # response.data is ordered to match the input batch
        embeddings.extend(item.embedding for item in response.data)

    return embeddings
