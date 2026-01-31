import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

# Project root (cine_ai_hackathon) so data/ lives there
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    PROJECT_NAME: str = "The Semantic Cut"
    API_V1_STR: str = "/api/v1"

    # Logging: DEBUG, INFO, WARNING, ERROR (env: LOG_LEVEL)
    LOG_LEVEL: str = "INFO"

    # OpenRouter: embeddings + optional LLM for query understanding
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_EMBEDDING_MODEL: str = "qwen/qwen3-embedding-8b"
    OPENROUTER_EMBEDDING_URL: str = "https://openrouter.ai/api/v1/embeddings"
    OPENROUTER_CHAT_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    # Chat for query understanding: use exact OpenRouter model id (e.g. openai/gpt-3.5-turbo; qwen ids may need hyphen: qwen/qwen-2.5-7b-instruct)
    OPENROUTER_CHAT_MODEL: str = "openai/gpt-3.5-turbo"
    # Qwen3-Embedding-8B default dimension (supports 32–4096)
    EMBEDDING_DIMENSION: int = 4096
    # Search: use LLM to parse query into intent (and optionally run hybrid intent + raw query)
    SEARCH_USE_QUERY_LLM: bool = True   # parse query into intent for embedding/rerank
    SEARCH_HYBRID_QUERY: bool = True   # if True, run intent + raw query and merge (RRF)
    # Retrieval: fetch this many from vector search, then rerank and return top SEARCH_RERANK_TOP
    SEARCH_INITIAL_K: int = 20   # more candidates → better rerank; 20 then top 5
    SEARCH_RERANK_TOP: int = 5   # number of results to return after rerank
    # If filtered search returns fewer than this, retry without filter and merge (avoids over-strict LLM filters)
    SEARCH_FILTER_FALLBACK_MIN: int = 5
    # Optional: drop results below this reranker score (e.g. 0.01 to hide very weak matches; 0 = no filter)
    SEARCH_RERANK_MIN_SCORE: float = 0.0

    # Vector DB
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    COLLECTION_NAME: str = "footage_transcripts_large"
    QDRANT_TIMEOUT: int = 120  # seconds for upsert/search (Qdrant Cloud may need longer for large batches)

    # Scene data: only this file is used for indexing
    GODFATHER_20_SCENES_JSON: str = str(DATA_DIR / "the_godfather_20scenes_with_actual_dialogs.json")

    # Video file for clip playback (served at GET /api/v1/video). Override with VIDEO_PATH in .env.
    VIDEO_PATH: str = os.getenv("VIDEO_PATH", str(PROJECT_ROOT / "The Godfather (1972) [1080p]" / "The.Godfather.1972.1080p.BrRip.x264.BOKUTOX.YIFY.mp4"))

    # SiliconFlow rerank (https://docs.siliconflow.com/en/api-reference/rerank/create-rerank)
    SILICONFLOW_API_KEY: str = os.getenv("SILICONFLOW_API_KEY", "")
    SILICONFLOW_RERANK_URL: str = "https://api.siliconflow.com/v1/rerank"
    RERANK_MODEL: str = "Qwen/Qwen3-Reranker-8B"

    # CORS: comma-separated list of allowed origins (e.g. deployed frontend URL)
    # Example: CORS_ORIGINS=https://myapp.vercel.app,https://www.myapp.com
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    class Config:
        case_sensitive = True


settings = Settings()
