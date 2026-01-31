# Semantic Footage Search Engine

Find footage using **intent-based queries**: editors describe what they want (e.g. “hesitant reaction before answering”, “someone begging for justice”) and get ranked clips with timestamps and match scores.

## Problem Statement Alignment (PS4)

| Requirement | Implementation |
|-------------|----------------|
| **Find footage using intent-based queries** | Query framed as “Find footage that shows: {query}”; embedding + rerank match by editorial intent, not keywords. |
| **Index footage using transcripts/captions** | Clip-level index from scene JSON (location, dialogue, clip description). |
| **Natural language queries** | Intent-based query instruction; vector retrieval + semantic rerank. |
| **Return clips with timestamps and relevance** | `start`/`end` (seconds), `start_display`/`end_display`, `score`, `match_score`, `confidence`. |
| **Text embeddings** | OpenRouter Qwen3-Embedding-8B. |
| **Vector DB / similarity search** | Qdrant (cosine similarity). |
| **Semantic ranking (not keyword)** | SiliconFlow Qwen3-Reranker-8B on full transcript. |
| **Max 20 clips** | Search `limit` capped at 20. |

## Retrieval & Ranking Logic

1. **Intent-based query embedding**  
   Query is prefixed with `"Find footage that shows: "` so the embedding model treats it as editorial intent (what the editor wants to see), not literal keywords.

2. **Vector retrieval**  
   Embedding is used to fetch `initial_k = max(limit × 3, 20)` nearest clips from Qdrant (cosine similarity). This gives a candidate set for reranking.

3. **Rerank**  
   Reranker receives the **full transcript** per clip (same text that was embedded), not just the short snippet. Ranking is therefore semantic over full context.

4. **Scores**  
   - `score`: raw reranker relevance (e.g. 0.3–0.7).  
   - `match_score`: normalized 0–1 in the returned batch (best = 1.0, worst = 0.0).  
   - `confidence`: High / Medium / Low from `score` bands.

5. **Output**  
   Each result includes `clip_id`, `scene_id`, `start`/`end` (seconds), `start_display`/`end_display`, snippet for UI, and metadata (location, actors, dialogue).

## Quick Start

- `.env`: `OPENROUTER_API_KEY`, `QDRANT_URL` (+ `QDRANT_API_KEY` for cloud), optional `SILICONFLOW_API_KEY` for rerank.
- Index: `python run_index_20scenes.py`
- API: `uvicorn app.main:app --reload` → `POST /api/v1/search` with `{"query": "...", "limit": 10}`
