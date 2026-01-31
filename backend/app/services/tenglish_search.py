"""
Tenglish (Telugu + English) semantic search: isolated RAG pipeline.
Uses OpenAI for embeddings, Qdrant for vector search. Optional local reranker.
"""
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Config from env (isolated from main app config)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
TELUGU_COLLECTION_NAME = os.getenv("TELUGU_COLLECTION_NAME", "ene_footage")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
TELUGU_SEARCH_INITIAL_K = int(os.getenv("TELUGU_SEARCH_INITIAL_K", "30"))
TELUGU_SEARCH_TOP = int(os.getenv("TELUGU_SEARCH_TOP", "10"))


def _get_openai_client():
    from openai import OpenAI
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for Telugu search. Set it in .env")
    return OpenAI(api_key=OPENAI_API_KEY)


def _get_qdrant_client():
    from qdrant_client import QdrantClient
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)


def get_embedding_openai(text: str) -> List[float]:
    """Generate embedding using OpenAI (sync)."""
    client = _get_openai_client()
    resp = client.embeddings.create(input=text, model=OPENAI_EMBEDDING_MODEL)
    return resp.data[0].embedding


def search_qdrant_telugu(
    query_vector: List[float],
    limit: int = 10,
    fetch_multiple: Optional[int] = None,
) -> List[Any]:
    """Vector search on Telugu collection. Returns list of points (payload + score)."""
    from qdrant_client import QdrantClient
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    k = fetch_multiple if fetch_multiple is not None else limit
    k = max(k, limit)
    response = client.query_points(
        collection_name=TELUGU_COLLECTION_NAME,
        query=query_vector,
        limit=k,
        with_payload=True,
        with_vectors=False,
    )
    return list(response.points or [])


def _payload_to_result(
    payload: Dict[str, Any],
    score: float,
    match_score: float,
    confidence: str,
) -> Dict[str, Any]:
    """Build a SearchResult-like dict from Qdrant payload."""
    text = payload.get("text") or payload.get("snippet") or ""
    clip_desc = payload.get("clip_description") or []
    if clip_desc and isinstance(clip_desc, list):
        display_text = " ".join(str(x) for x in clip_desc).strip()
    else:
        display_text = (text[:200] + "..." if len(text) > 200 else text) or "(no description)"
    return {
        "clip_id": payload.get("clip_id", "unknown"),
        "video_id": payload.get("scene_id"),
        "start": float(payload.get("start", 0)),
        "end": float(payload.get("end", 0)),
        "text": display_text,
        "score": score,
        "match_score": match_score,
        "confidence": confidence,
        "metadata": payload,
    }


def search_telugu_with_vector(query_vector: List[float], limit: int = 10) -> List[Dict[str, Any]]:
    """Vector search on Telugu collection and return SearchResult-like dicts (for streaming: embed elsewhere)."""
    k_fetch = min(TELUGU_SEARCH_INITIAL_K, limit * 3)
    points = search_qdrant_telugu(query_vector, limit=limit, fetch_multiple=k_fetch)
    if not points:
        return []
    n = min(len(points), limit)
    out = []
    for i, point in enumerate(points[:n]):
        payload = point.payload or {}
        raw_score = getattr(point, "score", 1.0)
        try:
            s = float(raw_score)
        except (TypeError, ValueError):
            s = 1.0
        match_score = 1.0 - (i / max(n - 1, 1)) if n > 1 else 1.0
        confidence = "High" if s >= 0.7 else "Medium" if s >= 0.5 else "Relevant"
        out.append(_payload_to_result(payload, s, round(match_score, 4), confidence))
    return out


def search_tenglish(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Full Tenglish RAG pipeline (sync):
    1. Embed query with OpenAI
    2. Vector search on Telugu collection
    3. Return top N as SearchResult-like dicts
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for Telugu search")
    query_vector = get_embedding_openai(query)
    return search_telugu_with_vector(query_vector, limit=limit)
