"""
Load scene/clip data from JSON files for indexing.
Supports: (1) scene-based JSON (20 scenes), (2) full transcript (YIFY subtitle lines).
"""
import json
import logging
from pathlib import Path
from typing import List, Optional

from app.core.utils import timestamp_to_seconds
from app.models.schemas import Scene, SceneDescription, Clip, Dialogue

logger = logging.getLogger(__name__)

# Chunk size for converting YIFY subtitle lines into clips (lines per clip)
YIFY_CLIP_LINES = 15


def load_scenes_json(path: Path) -> List[Scene]:
    """Load a JSON array of scenes (e.g. the_godfather_20scenes_with_actual_dialogs.json)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = [data]
    return [Scene(**s) for s in data]


def yify_line_to_dialogue(line: dict) -> Dialogue:
    """Convert one YIFY subtitle line to our Dialogue model."""
    start = line.get("start") or "00:00:00,000"
    end = line.get("end") or start
    text = (line.get("text") or "").replace("\n", " ").strip()
    return Dialogue(
        timestamp_start_sec=timestamp_to_seconds(start),
        timestamp_end_sec=timestamp_to_seconds(end),
        actor="Speaker",
        text=text,
        actual_dialogs=[text] if text else None,
    )


def load_yify_transcript(path: Path, lines_per_clip: int = YIFY_CLIP_LINES) -> List[Scene]:
    """
    Load YIFY-style subtitle JSON (flat list of {line, start, end, text})
    and convert to a list of Scene with Clip chunks for indexing.
    One scene 'yify_full' with clips = chunks of lines_per_clip lines.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = json.load(f)
    if not isinstance(lines, list):
        lines = []

    # Skip first line if it's credits/watermark
    if lines and isinstance(lines[0], dict):
        t0 = (lines[0].get("text") or "").lower()
        if "created" in t0 and "encoded" in t0:
            lines = lines[1:]

    scenes: List[Scene] = []
    scene_id = "yify_full"
    scene_desc = SceneDescription(
        int_ext="MIXED",
        location="Full film transcript",
        time_of_day="",
        actors_involved=[],
    )
    clips: List[Clip] = []
    for i in range(0, len(lines), lines_per_clip):
        chunk = lines[i : i + lines_per_clip]
        if not chunk:
            continue
        clip_id = f"yify_clip_{len(clips) + 1}"
        dialogue_list = [yify_line_to_dialogue(ln) for ln in chunk if isinstance(ln, dict)]
        if not dialogue_list:
            continue
        start_sec = dialogue_list[0].timestamp_start_sec
        end_sec = dialogue_list[-1].timestamp_end_sec
        clip_desc = [f"Subtitle segment {len(clips) + 1} ({start_sec:.0f}s–{end_sec:.0f}s)."]
        clips.append(
            Clip(
                clip_id=clip_id,
                clip_description=clip_desc,
                actors_involved=[],
                dialogue=dialogue_list,
            )
        )
    if clips:
        scenes.append(
            Scene(scene_id=scene_id, scene_description=scene_desc, clips=clips)
        )
        logger.info("Loaded YIFY transcript: %d lines → %d clips.", len(lines), len(clips))
    return scenes


def load_all_scenes(
    scenes_path: Path,
    transcript_path: Optional[Path] = None,
    lines_per_clip: int = YIFY_CLIP_LINES,
) -> List[Scene]:
    """
    Load all available scene data: scene-based JSON + optional full transcript.
    Returns a single list of Scene (all 20 scenes first, then yify_full if transcript_path given).
    """
    all_scenes: List[Scene] = []
    if scenes_path.exists():
        all_scenes = load_scenes_json(scenes_path)
        logger.info("Loaded %d scenes from %s.", len(all_scenes), scenes_path)
    if transcript_path and transcript_path.exists():
        yify_scenes = load_yify_transcript(transcript_path, lines_per_clip=lines_per_clip)
        all_scenes.extend(yify_scenes)
    return all_scenes
