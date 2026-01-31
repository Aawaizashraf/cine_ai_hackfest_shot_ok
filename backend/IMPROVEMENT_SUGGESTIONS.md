# Improvement Suggestions

## Architecture & Structure

1. **Single entrypoint** – You now have `main.py` re-exporting `app.main`. Prefer `uvicorn app.main:app` in docs/scripts so the entrypoint is explicit.

2. **Extract search pipeline** – Move the search logic (query understanding → embed → vector search → hybrid → rerank → build results) into a `app/services/search.py` function. Keeps `app/main.py` focused on HTTP and makes the pipeline easier to test.

3. **Async embedding/rerank** – `get_embedding`, `rerank`, and `parse_query` are synchronous. For better concurrency under load, consider `httpx.AsyncClient` and `async def` versions so multiple requests can overlap.

## Configuration

4. **Pydantic env handling** – `os.getenv()` in config is redundant; Pydantic Settings reads env vars. Use `Field(default="", env="OPENROUTER_API_KEY")` and drop manual `os.getenv` where possible.

5. **Config validation** – Add startup checks for required keys (e.g. `OPENROUTER_API_KEY`) and fail fast with clear errors instead of failing later in a service.

## Data & Indexing

6. **Batch embedding** – OpenRouter may support larger batches. Experiment with batch size (e.g. 50–100) to reduce round trips during indexing.

7. **Index idempotency** – Support upsert-by-clip_id without `recreate_collection` so you can add/update clips without wiping the collection.

8. **Estimated timestamps validator** – Add a Pydantic validator on `Clip` for `estimated_clip_start`/`estimated_clip_end` that parses strings to float so indexing logic stays simple.

## Search Quality

9. **Keyword boosting** – Use `parsed.keywords` from query understanding to boost clips that contain those terms (e.g. in metadata or text) during rerank or as a post-filter.

10. **Reranker fallback** – When `SILICONFLOW_API_KEY` is missing, the reranker returns `(i, 0.0)` for all items. Consider preserving vector-search order or using a simple heuristic (e.g. TF-IDF) instead of uniform scores.

## Testing & Observability

11. **Unit tests** – Add tests for `_build_embed_text`, `_build_snippet`, `_rrf_merge`, `timestamp_to_seconds`, and `parse_query` (with mocked HTTP).

12. **Integration test** – A minimal test that indexes 1–2 clips and runs a search to validate the full pipeline.

13. **Structured logging** – Use `structlog` or JSON logs with `request_id` for easier tracing and debugging in production.

## API & UX

14. **Search response metadata** – Include `query_used` (intent or raw) and `num_candidates` in the response so clients know what was searched.

15. **Pagination** – If you increase `SEARCH_RERANK_TOP` or support larger limits, add `offset`/`limit` or cursor-based pagination.

16. **Health check** – Add `GET /health` that checks Qdrant connectivity and optional API keys so load balancers can probe liveness.

## Security & Performance

17. **Rate limiting** – Add rate limiting (e.g. `slowapi`) on `/search` and `/index` to protect against abuse.

18. **Caching** – Cache embeddings for repeated queries (e.g. Redis or in-memory with TTL) to reduce OpenRouter calls.

19. **Input validation** – Sanitize/limit query length (e.g. max 500 chars) to avoid oversized requests.
