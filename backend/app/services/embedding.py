"""
OpenRouter embeddings using Qwen3-Embedding-8B.
Uses OpenAI-compatible embeddings API: POST https://openrouter.ai/api/v1/embeddings
"""
import logging
from typing import Union, List

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_embedding(text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Encode text(s) to embedding(s) via OpenRouter (Qwen3-Embedding-8B).
    - Single string -> list of floats (one vector).
    - List of strings -> list of lists (batch of vectors).
    """
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is required for embeddings.")

    if isinstance(text, str):
        text = [text]
    if not text:
        logger.debug("get_embedding: empty input, returning [].")
        return []

    batch_size = len(text)
    preview = text[0][:60] + "..." if len(text[0]) > 60 else text[0]
    logger.info("get_embedding: batch_size=%d, model=%s, preview=%r", batch_size, settings.OPENROUTER_EMBEDDING_MODEL, preview)
    url = settings.OPENROUTER_EMBEDDING_URL
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.OPENROUTER_EMBEDDING_MODEL,
        "input": text,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    # OpenAI-compatible response: data["data"] is list of { "embedding": [...], "index": i }
    items = data.get("data", [])
    items.sort(key=lambda x: x.get("index", 0))
    embeddings = [item["embedding"] for item in items]
    dim = len(embeddings[0]) if embeddings else 0
    logger.info("get_embedding: received %d vectors, dim=%d.", len(embeddings), dim)

    if len(embeddings) == 1 and len(text) == 1:
        return embeddings[0]
    return embeddings
