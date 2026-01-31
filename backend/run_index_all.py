#!/usr/bin/env python3
"""
Index all scenes from the_godfather_20scenes_with_actual_dialogs.json into Qdrant.

Run from project root:
    uv run python run_index_all.py

Options:
    --no-recreate   Do not recreate Qdrant collection (append to existing).

Requires .env with OPENROUTER_API_KEY and optionally QDRANT_URL / QDRANT_API_KEY.
"""
import argparse
import logging
import sys
from pathlib import Path

from app.core.config import settings
from app.data.loaders import load_scenes_json
from app.main import index_scenes_sync

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Index all scenes from 20-scene JSON")
    parser.add_argument(
        "--no-recreate",
        action="store_true",
        help="Do not recreate Qdrant collection (append to existing)",
    )
    args = parser.parse_args()

    scenes_path = Path(settings.GODFATHER_20_SCENES_JSON)
    if not scenes_path.exists():
        logger.error("Data file not found: %s", scenes_path)
        sys.exit(1)

    logger.info("Loading %s...", scenes_path)
    scenes_list = load_scenes_json(scenes_path)
    total_clips = sum(len(s.clips) for s in scenes_list)
    logger.info("Total: %d scenes, %d clips.", len(scenes_list), total_clips)

    try:
        result = index_scenes_sync(scenes_list, recreate_collection=not args.no_recreate)
        logger.info("%s", result.get("message", result))
    except Exception as e:
        logger.exception("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
