"""
FastAPI app: index clips into Qdrant, search by natural language.
Embeddings via OpenRouter (Qwen3-Embedding-8B).
"""
import asyncio
import json
import logging
import time
import uuid

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import settings
from app.core.utils import seconds_to_display, timestamp_to_seconds
from app.models.schemas import IndexRequest, SearchRequest, SearchResult, Scene
from app.services.embedding import get_embedding
from app.services.vector_db import vector_db
from app.services.rerank import rerank
from app.services.query_understanding import parse_query
from app.services import tenglish_search

_LOG_LEVELS = {"DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING, "ERROR": logging.ERROR}
_level = _LOG_LEVELS.get((getattr(settings, "LOG_LEVEL", "INFO") or "INFO").upper(), logging.INFO)
logging.basicConfig(level=_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS: localhost + any origins from env (e.g. deployed frontend)
_cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_extra = getattr(settings, "CORS_ORIGINS", "") or ""
_cors_origins.extend(o.strip() for o in _extra.split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def log_search_config():
    """Log active search config so you can confirm LLM + hybrid + rerank are in use."""
    use_llm = getattr(settings, "SEARCH_USE_QUERY_LLM", True)
    hybrid = getattr(settings, "SEARCH_HYBRID_QUERY", False)
    initial_k = getattr(settings, "SEARCH_INITIAL_K", 20)
    return_top = getattr(settings, "SEARCH_RERANK_TOP", 5)
    logger.info(
        "Semantic search config: use_llm=%s, hybrid=%s, initial_k=%d, return_top=%d (run uvicorn app.main:app for this pipeline)",
        use_llm, hybrid, initial_k, return_top,
    )


def _build_embed_text(scene: Scene, clip) -> str:
    """Build the single text blob to embed (semantic only)."""
    parts = [
        scene.scene_description.location or "",
        scene.scene_description.time_of_day or "",
        " ".join(scene.scene_description.actors_involved or []),
        " ".join(clip.clip_description or []),
    ]
    for d in clip.dialogue:
        line = f"{d.actor}: {d.text}"
        if getattr(d, "actual_dialogs", None):
            line += " " + " ".join(d.actual_dialogs).replace("\n", " ")
        parts.append(line)
    return " ".join(p for p in parts if p).strip()


def _build_snippet(clip, max_chars: int = 120) -> str:
    """First line of dialogue or clip_description for card preview."""
    if clip.dialogue and clip.dialogue[0].text:
        return (clip.dialogue[0].text or "")[:max_chars]
    if clip.clip_description:
        return " ".join(clip.clip_description)[:max_chars]
    return ""


@app.get("/")
def read_root():
    return {"message": "Welcome to the Semantic Footage Search Engine API"}


@app.get(f"{settings.API_V1_STR}/video")
def get_video():
    """Serve the movie file for clip playback. Supports Range requests for seeking."""
    path = Path(getattr(settings, "VIDEO_PATH", ""))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Video file not found. Set VIDEO_PATH in config or .env.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
    )


@app.post(f"{settings.API_V1_STR}/index")
async def index_scenes(request: IndexRequest):
    """Index scenes: build embed text per clip, embed via OpenRouter, upsert to Qdrant."""
    start_time = time.time()
    logger.info("Index request started: %d scenes, recreate_collection=%s", len(request.scenes), request.recreate_collection)
    try:
        if request.recreate_collection:
            logger.info("Recreating Qdrant collection as requested.")
            vector_db.recreate_collection()

        segments_to_add = []
        texts_to_embed = []

        for scene in request.scenes:
            for clip in scene.clips:
                text_to_embed = _build_embed_text(scene, clip)

                if clip.dialogue:
                    start_sec = min(d.timestamp_start_sec for d in clip.dialogue)
                    end_sec = max(d.timestamp_end_sec for d in clip.dialogue)
                else:
                    # Use estimated_clip_start/end when dialogue is empty
                    start_sec = timestamp_to_seconds(getattr(clip, "estimated_clip_start", None) or 0)
                    end_sec = timestamp_to_seconds(getattr(clip, "estimated_clip_end", None) or 0)

                start_display = seconds_to_display(start_sec)
                end_display = seconds_to_display(end_sec)
                snippet = _build_snippet(clip)
                clip_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, clip.clip_id))
                dialogue_payload = [d.model_dump() for d in clip.dialogue]

                segment_data = {
                    "id": clip_uuid,
                    "clip_id": clip.clip_id,
                    "scene_id": scene.scene_id,
                    "location": scene.scene_description.location,
                    "int_ext": scene.scene_description.int_ext,
                    "time_of_day": scene.scene_description.time_of_day,
                    "actors": clip.actors_involved,
                    "clip_description": clip.clip_description,
                    "dialogue": dialogue_payload,
                    "start": start_sec,
                    "end": end_sec,
                    "start_display": start_display,
                    "end_display": end_display,
                    "snippet": snippet,
                    "text": text_to_embed,
                }
                segments_to_add.append(segment_data)
                texts_to_embed.append(text_to_embed)

        if not segments_to_add:
            logger.warning("Index request produced no clips to index.")
            return {"message": "No clips to index."}

        logger.info("Building embeddings for %d clips via OpenRouter...", len(texts_to_embed))
        embeddings = get_embedding(texts_to_embed)
        logger.info("Upserting %d segments to Qdrant collection '%s'.", len(segments_to_add), vector_db.collection_name)
        vector_db.add_segments(segments_to_add, embeddings)

        duration = time.time() - start_time
        logger.info("Index completed: %d clips indexed in %.2f s.", len(segments_to_add), duration)
        return {"message": f"Successfully indexed {len(segments_to_add)} clips in {duration:.2f} seconds."}

    except Exception as e:
        logger.error(f"Indexing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _rrf_merge(runs: list, k: int = 60) -> list:
    """Merge multiple ranked lists of points by Reciprocal Rank Fusion. Dedupe by clip_id, order by RRF score."""
    rrf_scores = {}  # clip_id -> (rrf_score, point)
    for run in runs:
        for rank, point in enumerate(run):
            meta = point.payload or {}
            cid = meta.get("clip_id") or str(getattr(point, "id", rank))
            rrf_scores[cid] = (
                rrf_scores.get(cid, (0.0, None))[0] + 1.0 / (k + rank + 1),
                point,
            )
    # Sort by RRF score desc, return list of points
    ordered = sorted(rrf_scores.values(), key=lambda x: -x[0])
    return [p for _, p in ordered]


@app.post(f"{settings.API_V1_STR}/search", response_model=list[SearchResult])
async def search_footage(request: SearchRequest):
    """Search: optional LLM query parsing (intent) → embed → vector search → optional hybrid merge → rerank → return."""
    try:
        logger.info("Search request: query=%r, limit=%d", request.query[:80] + ("..." if len(request.query) > 80 else ""), request.limit)
        use_llm = getattr(settings, "SEARCH_USE_QUERY_LLM", True)
        hybrid = getattr(settings, "SEARCH_HYBRID_QUERY", False)
        logger.info("Search config: use_llm=%s, hybrid=%s", use_llm, hybrid)

        # Query text for embedding and rerank: intent + filters (from LLM) or raw, no explicit filters
        parsed = None
        if use_llm:
            logger.info("Query understanding: calling LLM to parse intent and filters...")
            parsed = parse_query(request.query)
            intent_text = parsed.intent or request.query
            logger.info("Query understanding: intent=%r, keywords=%s, filters=%s", intent_text[:100] + ("..." if len(intent_text) > 100 else ""), getattr(parsed, "keywords", []), getattr(parsed, "filters", {}))
        else:
            intent_text = request.query
            logger.info("Query understanding: skipped (use_llm=false), using raw query as intent.")

        # Filters come only from LLM (input is query only)
        search_filters = None
        if parsed and getattr(parsed, "filters", None):
            # Drop keys with empty values; pass to vector DB only if non-empty
            search_filters = {k: v for k, v in parsed.filters.items() if v}
            if not search_filters:
                search_filters = None
            else:
                logger.info("Search filters (from LLM): %s", search_filters)

        query_for_embed = f"Find footage that shows: {intent_text}"
        logger.info("Embedding query (intent) for vector search...")
        query_embedding = get_embedding(query_for_embed)
        if not isinstance(query_embedding[0], (int, float)):
            query_embedding = query_embedding[0]

        initial_k = getattr(settings, "SEARCH_INITIAL_K", 20)
        return_top = getattr(settings, "SEARCH_RERANK_TOP", 5)
        fallback_min = getattr(settings, "SEARCH_FILTER_FALLBACK_MIN", 5)
        logger.info("Vector search: fetching top %d candidates from Qdrant.", initial_k)
        search_results = vector_db.search(query_embedding, n_results=initial_k, filters=search_filters)
        logger.info("Vector search: returned %d points.", len(search_results))

        # If filter was applied and returned too few, retry without filter and merge (filtered first, then fill)
        if search_filters and len(search_results) < fallback_min:
            logger.info("Filter returned %d < %d; fallback search without filter.", len(search_results), fallback_min)
            unfiltered = vector_db.search(query_embedding, n_results=initial_k, filters=None)
            seen_clip_ids = {(p.payload or {}).get("clip_id") or getattr(p, "id") for p in search_results}
            for point in unfiltered:
                cid = (point.payload or {}).get("clip_id") or getattr(point, "id", None)
                if cid not in seen_clip_ids:
                    search_results.append(point)
                    seen_clip_ids.add(cid)
                    if len(search_results) >= initial_k:
                        break
            search_results = search_results[:initial_k]
            logger.info("After fallback merge: %d candidates.", len(search_results))

        if hybrid and intent_text.strip().lower() != request.query.strip().lower():
            logger.info("Hybrid: running second vector search with raw query, then RRF merge.")
            raw_embed = get_embedding(f"Find footage that shows: {request.query}")
            if not isinstance(raw_embed[0], (int, float)):
                raw_embed = raw_embed[0]
            raw_results = vector_db.search(raw_embed, n_results=initial_k, filters=search_filters)
            logger.info("Hybrid: raw search returned %d points; merging with RRF.", len(raw_results))
            search_results = _rrf_merge([search_results, raw_results])[:initial_k]
            logger.info("Hybrid: after RRF merge, %d candidates.", len(search_results))

        if not search_results:
            logger.info("Search: no candidates; returning empty list.")
            return []

        # Build candidates: full transcript for reranker, snippet for display
        candidates = []
        for point in search_results:
            meta = point.payload or {}
            full_text = meta.get("text", "") or ""
            snippet = meta.get("snippet", "") or full_text[:120] or "(no text)"
            candidates.append({"point": point, "meta": meta, "full_text": full_text, "snippet": snippet})
        documents = [c["full_text"] or c["snippet"] or "(no text)" for c in candidates]
        logger.info("Rerank: sending %d candidates to SiliconFlow (full transcript per candidate).", len(documents))

        # Rerank using intent (or raw if no LLM), then return only top SEARCH_RERANK_TOP
        rerank_query = intent_text if use_llm else request.query
        return_top = getattr(settings, "SEARCH_RERANK_TOP", 5)
        logger.info("Rerank: query=%r, top_n=%d.", rerank_query[:60] + ("..." if len(rerank_query) > 60 else ""), return_top)
        reranked = rerank(rerank_query, documents, top_n=return_top)
        logger.info("Rerank: received %d scored results.", len(reranked))

        # Collect valid (idx, score), apply optional min-score filter
        min_score = getattr(settings, "SEARCH_RERANK_MIN_SCORE", 0.0)
        items = []
        seen_idx = set()
        for idx, score in reranked:
            if idx >= len(candidates):
                continue
            try:
                s = float(score) if score is not None else 0.0
            except (TypeError, ValueError):
                s = 0.0
            if s >= min_score:
                items.append((idx, s))
                seen_idx.add(idx)

        # If reranker returned fewer than return_top, fill with next-best by vector order (score 0 → Low confidence)
        while len(items) < return_top and len(items) < len(candidates):
            for i in range(len(candidates)):
                if i not in seen_idx:
                    items.append((i, 0.0))
                    seen_idx.add(i)
                    break
            else:
                break

        if not items:
            logger.info("Search: no valid reranked items above min_score=%.4f; returning empty list.", min_score)
            return []

        n = len(items)
        if min_score > 0:
            logger.info("Search: after min_score=%.4f filter, %d results.", min_score, n)
        if n > len(reranked):
            logger.info("Search: filled to %d results (reranker returned %d).", n, len(reranked))
        out = []
        clip_ids_out = []
        for i, (idx, raw_score) in enumerate(items):
            c = candidates[idx]
            meta = c["meta"]
            # Rank-based match_score: first result = 1.0, last = 0.0 (no dependency on API score format)
            if n <= 1:
                match_score = 1.0
            else:
                match_score = round(1.0 - (i / (n - 1)), 4)  # 1.0, 0.75, 0.5, 0.25, 0.0 for n=5
            confidence = "Low"
            if raw_score >= 0.5:
                confidence = "High"
            elif raw_score >= 0.35:
                confidence = "Medium"
            cid = meta.get("clip_id", "unknown")
            clip_ids_out.append(cid)
            # text = clip_description (what the clip depicts); fallback to snippet if empty
            clip_desc = meta.get("clip_description") or []
            display_text = " ".join(clip_desc).strip() if clip_desc else c["snippet"]
            out.append(
                SearchResult(
                    clip_id=cid,
                    video_id=meta.get("scene_id"),
                    start=meta.get("start", 0.0),
                    end=meta.get("end", 0.0),
                    text=display_text or c["snippet"],
                    score=raw_score,
                    match_score=match_score,
                    confidence=confidence,
                    metadata=meta,
                )
            )
        logger.info("Search completed: returning %d results, clip_ids=%s.", len(out), clip_ids_out)
        return out

    except Exception as e:
        logger.error("Search error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _format_sse(data: dict) -> str:
    """Format as Server-Sent Event for streaming (e.g. AI SDK / EventSource)."""
    return f"data:{json.dumps(data)}\n\n"


async def _run_search_stream(request: SearchRequest, req: Request):
    """Async generator: same pipeline as search_footage but yields SSE status events step by step."""
    use_llm = getattr(settings, "SEARCH_USE_QUERY_LLM", True)
    hybrid = getattr(settings, "SEARCH_HYBRID_QUERY", False)
    initial_k = getattr(settings, "SEARCH_INITIAL_K", 20)
    return_top = getattr(settings, "SEARCH_RERANK_TOP", 5)

    try:
        # --- Query understanding ---
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "query_understanding", "status": "loading", "message": "Understanding query..."},
        })
        if use_llm:
            parsed = await asyncio.to_thread(parse_query, request.query)
            intent_text = parsed.intent or request.query
            search_filters = None
            if getattr(parsed, "filters", None):
                search_filters = {k: v for k, v in parsed.filters.items() if v}
                if not search_filters:
                    search_filters = None
        else:
            parsed = None
            intent_text = request.query
            search_filters = None

        yield _format_sse({
            "type": "data-status",
            "data": {
                "id": "query_understanding",
                "status": "done",
                "message": f"Intent: {intent_text[:80]}{'...' if len(intent_text) > 80 else ''}",
                "intent_preview": intent_text[:120],
                "filters": search_filters,
            },
        })

        # --- Embedding ---
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "embedding", "status": "loading", "message": "Embedding query..."},
        })
        query_for_embed = f"Find footage that shows: {intent_text}"
        query_embedding = await asyncio.to_thread(get_embedding, query_for_embed)
        if not isinstance(query_embedding[0], (int, float)):
            query_embedding = query_embedding[0]
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "embedding", "status": "done", "message": "Query embedded"},
        })

        # --- Vector search ---
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "vector_search", "status": "loading", "message": "Searching clips..."},
        })
        fallback_min = getattr(settings, "SEARCH_FILTER_FALLBACK_MIN", 5)
        search_results = await asyncio.to_thread(
            vector_db.search, query_embedding, initial_k, search_filters
        )
        if search_filters and len(search_results) < fallback_min:
            unfiltered = await asyncio.to_thread(
                vector_db.search, query_embedding, initial_k, None
            )
            seen_clip_ids = {(p.payload or {}).get("clip_id") or getattr(p, "id") for p in search_results}
            for point in unfiltered:
                cid = (point.payload or {}).get("clip_id") or getattr(point, "id", None)
                if cid not in seen_clip_ids:
                    search_results.append(point)
                    seen_clip_ids.add(cid)
                    if len(search_results) >= initial_k:
                        break
            search_results = search_results[:initial_k]
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "vector_search", "status": "done", "message": f"Found {len(search_results)} candidates"},
        })

        if hybrid and intent_text.strip().lower() != request.query.strip().lower():
            yield _format_sse({
                "type": "data-status",
                "data": {"id": "hybrid", "status": "loading", "message": "Merging with raw query..."},
            })
            raw_embed = await asyncio.to_thread(get_embedding, f"Find footage that shows: {request.query}")
            if not isinstance(raw_embed[0], (int, float)):
                raw_embed = raw_embed[0]
            raw_results = await asyncio.to_thread(
                vector_db.search, raw_embed, initial_k, search_filters
            )
            search_results = _rrf_merge([search_results, raw_results])[:initial_k]
            yield _format_sse({
                "type": "data-status",
                "data": {"id": "hybrid", "status": "done", "message": f"Merged to {len(search_results)} candidates"},
            })

        if not search_results:
            yield _format_sse({"type": "results", "data": []})
            yield "data:[DONE]\n\n"
            return

        # --- Build candidates for rerank ---
        candidates = []
        for point in search_results:
            meta = point.payload or {}
            full_text = meta.get("text", "") or ""
            snippet = meta.get("snippet", "") or full_text[:120] or "(no text)"
            candidates.append({"point": point, "meta": meta, "full_text": full_text, "snippet": snippet})
        documents = [c["full_text"] or c["snippet"] or "(no text)" for c in candidates]

        # --- Rerank ---
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "rerank", "status": "loading", "message": "Reranking results..."},
        })
        rerank_query = intent_text if use_llm else request.query
        reranked = await asyncio.to_thread(rerank, rerank_query, documents, top_n=return_top)
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "rerank", "status": "done", "message": f"Reranked to top {return_top}"},
        })

        min_score = getattr(settings, "SEARCH_RERANK_MIN_SCORE", 0.0)
        items = []
        seen_idx = set()
        for idx, score in reranked:
            if idx >= len(candidates):
                continue
            try:
                s = float(score) if score is not None else 0.0
            except (TypeError, ValueError):
                s = 0.0
            if s >= min_score:
                items.append((idx, s))
                seen_idx.add(idx)

        # If reranker returned fewer than return_top, fill with next-best by vector order
        while len(items) < return_top and len(items) < len(candidates):
            for i in range(len(candidates)):
                if i not in seen_idx:
                    items.append((i, 0.0))
                    seen_idx.add(i)
                    break
            else:
                break

        if not items:
            yield _format_sse({"type": "results", "data": []})
            yield "data:[DONE]\n\n"
            return

        n = len(items)
        out = []
        for i, (idx, raw_score) in enumerate(items):
            c = candidates[idx]
            meta = c["meta"]
            if n <= 1:
                match_score = 1.0
            else:
                match_score = round(1.0 - (i / (n - 1)), 4)
            confidence = "Low"
            if raw_score >= 0.5:
                confidence = "High"
            elif raw_score >= 0.35:
                confidence = "Medium"
            clip_desc = meta.get("clip_description") or []
            display_text = " ".join(clip_desc).strip() if clip_desc else c["snippet"]
            out.append(
                SearchResult(
                    clip_id=meta.get("clip_id", "unknown"),
                    video_id=meta.get("scene_id"),
                    start=meta.get("start", 0.0),
                    end=meta.get("end", 0.0),
                    text=display_text or c["snippet"],
                    score=raw_score,
                    match_score=match_score,
                    confidence=confidence,
                    metadata=meta,
                )
            )

        yield _format_sse({"type": "results", "data": [r.model_dump(mode="json") for r in out]})
        yield "data:[DONE]\n\n"

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Search stream error: %s", e, exc_info=True)
        yield _format_sse({"type": "error", "errorText": str(e)})


@app.post(f"{settings.API_V1_STR}/search/stream")
async def search_footage_stream(request: SearchRequest, req: Request):
    """Streaming search: same as POST /search but yields SSE status events (query_understanding, embedding, vector_search, rerank, results) step by step."""
    return StreamingResponse(
        _run_search_stream(request, req),
        media_type="text/event-stream",
        headers={
            "x-vercel-ai-ui-message-stream": "v1",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_telugu_search_stream(request: SearchRequest):
    """Streaming Telugu/Tenglish search: OpenAI embed -> Qdrant -> results (same SSE format as main search)."""
    try:
        limit = min(max(1, request.limit), 20)
        # --- Embedding ---
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "embedding", "status": "loading", "message": "Embedding query (OpenAI)..."},
        })
        query_vector = await asyncio.to_thread(
            tenglish_search.get_embedding_openai, request.query
        )
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "embedding", "status": "done", "message": "Query embedded"},
        })

        # --- Vector search ---
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "vector_search", "status": "loading", "message": "Searching Telugu clips..."},
        })
        results = await asyncio.to_thread(
            tenglish_search.search_telugu_with_vector, query_vector, limit
        )
        yield _format_sse({
            "type": "data-status",
            "data": {"id": "vector_search", "status": "done", "message": f"Found {len(results)} results"},
        })

        yield _format_sse({"type": "results", "data": results})
        yield "data:[DONE]\n\n"
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error("Telugu search stream error: %s", e, exc_info=True)
        yield _format_sse({"type": "error", "errorText": str(e)})


@app.post(f"{settings.API_V1_STR}/telugu-search/stream")
async def telugu_search_stream(request: SearchRequest):
    """Streaming Telugu/Tenglish search: OpenAI embeddings + Qdrant. Isolated from main search pipeline."""
    return StreamingResponse(
        _run_telugu_search_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def index_scenes_sync(scenes, recreate_collection: bool):
    """Synchronous indexing for standalone script. scenes: list of dict or Scene."""
    import asyncio

    scenes_list = [Scene(**s) if not isinstance(s, Scene) else s for s in scenes]
    request = IndexRequest(scenes=scenes_list, recreate_collection=recreate_collection)
    return asyncio.run(index_scenes(request))
