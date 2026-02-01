"""
SiliconFlow rerank API: https://docs.siliconflow.com/en/api-reference/rerank/create-rerank
POST /v1/rerank with query + documents, returns results sorted by relevance_score.
On API error (e.g. 500), falls back to original document order so search still returns results.
"""
import logging
from typing import List, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def rerank(query: str, documents: List[str], top_n: int | None = None) -> List[Tuple[int, float]]:
    """
    Rerank documents by relevance to the query using SiliconFlow (Qwen3-Reranker).
    - query: search query string.
    - documents: list of candidate text strings (same order as your candidates).
    - top_n: number of top results to return (default: all, in sorted order).
    Returns: list of (original_index, relevance_score) sorted by score descending.
    """
    if not documents:
        logger.debug("rerank: no documents, returning [].")
        return []
    if not settings.SILICONFLOW_API_KEY:
        logger.warning("SILICONFLOW_API_KEY not set; skipping rerank, returning order unchanged.")
        return [(i, 0.0) for i in range(len(documents))]

    def _fallback():
        """On API error, return original document order (first top_n) so search still completes."""
        n = len(documents)
        k = min(n, top_n) if top_n is not None else n
        return [(i, 0.0) for i in range(k)]

    logger.info("rerank: query=%r, num_documents=%d, top_n=%s, model=%s", query[:60] + ("..." if len(query) > 60 else ""), len(documents), top_n, settings.RERANK_MODEL)
    url = settings.SILICONFLOW_RERANK_URL
    headers = {
        "Authorization": f"Bearer {settings.SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.RERANK_MODEL,
        "query": query,
        "documents": documents,
        "return_documents": False,
    }
    if top_n is not None:
        payload["top_n"] = top_n

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.warning("rerank: API error %s (%s); using vector order.", e.response.status_code, e)
        return _fallback()
    except Exception as e:
        logger.warning("rerank: request failed (%s); using vector order.", e)
        return _fallback()

    # Response: { "results": [ { "index": int, "relevance_score": float, ... }, ... ] }
    results = data.get("results", [])
    out = []
    for item in results:
        idx = item.get("index", len(out))
        raw = item.get("relevance_score", item.get("score", 0.0))
        out.append((idx, float(raw) if raw is not None else 0.0))
    logger.info("rerank: received %d scored results.", len(out))
    return out
