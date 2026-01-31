#!/usr/bin/env python3
"""
Index scene-based JSON (default: 20 scenes) into Qdrant using OpenRouter (Qwen3-Embedding-8B).

Run from project root:
    uv run python run_index_20scenes.py
    uv run python run_index_20scenes.py /path/to/scenes.json

To index all 20 scenes (same as run_index_all.py):
    uv run python run_index_all.py

Requires .env with OPENROUTER_API_KEY and optionally QDRANT_URL / QDRANT_API_KEY.
"""
import argparse
import sys
from pathlib import Path

from app.core.config import settings
from app.data.loaders import load_scenes_json
from app.main import index_scenes_sync


def main():
    parser = argparse.ArgumentParser(description="Index scene JSON into Qdrant")
    parser.add_argument(
        "data_path",
        nargs="?",
        default=None,
        help="Path to scene JSON (default: GODFATHER_20_SCENES_JSON)",
    )
    parser.add_argument("--no-recreate", action="store_true", help="Do not recreate collection")
    args = parser.parse_args()

    data_path = Path(args.data_path or settings.GODFATHER_20_SCENES_JSON)
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        sys.exit(1)

    print(f"Loading {data_path}...")
    scenes = load_scenes_json(data_path)
    total_clips = sum(len(s.clips) for s in scenes)
    print(f"Parsed {len(scenes)} scenes, {total_clips} clips.")

    print("Building embeddings (OpenRouter Qwen3-Embedding-8B) and upserting to Qdrant...")
    try:
        result = index_scenes_sync(scenes, recreate_collection=not args.no_recreate)
        print(result.get("message", result))
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
