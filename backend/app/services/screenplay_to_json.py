"""
Convert screenplay/transcript text to structured JSON using OpenRouter chat.
Isolated service for the screenplay-to-JSON route; no dependency on search or Qdrant.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SCREENPLAY_SYSTEM_PROMPT = """You are a screenplay-to-JSON converter. Your task is to convert movie/TV screenplay scenes into structured JSON format for a semantic video search system.

## INPUT FORMAT
You will receive a screenplay scene in standard screenplay format with:
Scene heading (e.g., "1 INT. CAR - DAY 1")
Action descriptions (visual descriptions of what happens)
Character names in CAPS followed by their dialogue
Parentheticals (actor directions)
Scene transitions

## OUTPUT FORMAT
Generate a JSON object with the following structure:

{
    "scene_id": "scene_X",
    "scene_description": {
        "int_ext": "INT" or "EXT",
        "location": "LOCATION_NAME",
        "time_of_day": "DAY/NIGHT/EVENING/CONTINUOUS/MOMENTS LATER",
        "actors_involved": ["ACTOR1", "ACTOR2", ...]
    },
    "clips": [
        {
            "clip_id": "scene_X_clip_Y",
            "clip_description": [
                "Visual description sentence 1",
                "Visual description sentence 2",
                ...
            ],
            "actors_involved": ["ACTOR1", "ACTOR2"],
            "dialogue": [
                {
                    "timestamp_start_sec": 0.0,
                    "timestamp_end_sec": 4.0,
                    "actor": "ACTOR_NAME",
                    "text": "dialogue text"
                }
            ]
        }
    ]
}

## CONVERSION RULES

### 1. Scene Information
Extract scene number from scene heading (e.g., "1 INT. CAR - DAY" → scene_id: "scene_1")
Parse INT/EXT from scene heading
Extract location (everything between INT/EXT and time of day)
Extract time_of_day (last part of scene heading: DAY, NIGHT, EVENING, CONTINUOUS, etc.)
List all unique character names that appear in the scene

### 2. Clip Segmentation
Break the scene into logical clips based on:
**Action changes**: New visual action or camera focus
**Dialogue exchanges**: Group 2-6 related dialogue exchanges together
**Beats/Moments**: Significant emotional or narrative beats
**Location micro-changes**: Character moves within same scene location
Each clip should be 20-60 seconds of screen time (estimate based on dialogue/action)

### 3. Clip Descriptions
Extract ALL action lines (non-dialogue text) and convert to clip_description array
Each sentence becomes a separate array element
Include visual details: character emotions, movements, environment
Preserve camera directions if mentioned (close-up, wide shot, etc.)
Keep descriptions objective and visual (what camera sees)
Include character blocking and physical reactions

### 4. Dialogue Timestamps
Start first dialogue at timestamp_start_sec: 0.0 for each clip
Estimate dialogue duration:
  - Short line (1-5 words): ~2-3 seconds
  - Medium line (6-15 words): ~3-5 seconds
  - Long line (16-30 words): ~5-8 seconds
  - Very long monologue (30+ words): ~8-15 seconds
Add 0.5 second pause between dialogue exchanges
Keep running count within each clip
Format: Use one decimal place (e.g., 4.5, not 4.50)

### 5. Handling Special Cases
**Continued dialogue** (CONT'D): Treat as continuation, don't split
**Parentheticals**: Ignore in dialogue text, but incorporate into clip_description if visual (e.g., "(laughs)" → add to description)
**Action during dialogue**: Include in clip_description
**No dialogue clips**: Leave dialogue array empty []
**Multiple actors in one clip**: List all in actors_involved
**Multilingual dialogue** (Telugu/English mix): Preserve exact text as written

### 6. Clip Naming Convention
Format: "scene_{scene_number}_clip_{clip_number}"
Number clips sequentially: clip_1, clip_2, clip_3, etc.

## QUALITY CHECKLIST
Before outputting, verify:
[ ] All actor names are in CAPS
[ ] Timestamps increment logically within each clip
[ ] All visual action is captured in clip_description
[ ] Dialogue text is verbatim from screenplay (including Tenglish/multilingual)
[ ] Each clip has a unique clip_id
[ ] actors_involved lists only actors present in that specific clip
[ ] No dialogue is missing
[ ] Scene metadata (int_ext, location, time_of_day) is accurate

Output only valid JSON. No markdown code fences, no explanation before or after."""


def _extract_json_from_content(content: str) -> Optional[str]:
    """Strip markdown code blocks if present and return raw JSON string."""
    text = content.strip()
    # Remove ```json ... ``` or ``` ... ```
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            text = match.group(1).strip()
        else:
            lines = text.split("\n")
            out = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if not in_block:
                    out.append(line)
            text = "\n".join(out)
    return text if text else None


def screenplay_to_json(transcript: str) -> Dict[str, Any]:
    """
    Convert screenplay/transcript text to structured JSON via OpenRouter chat.
    Returns the parsed JSON object. Raises ValueError on empty input or API/parse failure.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty")

    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set")

    user_message = (
        "Now, convert the following screenplay scene into JSON:\n\n" + transcript.strip()
    )

    logger.info(
        "screenplay_to_json: calling OpenRouter chat (model=%s)",
        getattr(settings, "OPENROUTER_CHAT_MODEL", "?"),
    )
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                settings.OPENROUTER_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/cine-ai-hackathon",
                },
                json={
                    "model": settings.OPENROUTER_CHAT_MODEL,
                    "messages": [
                        {"role": "system", "content": SCREENPLAY_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 4096,
                },
            )
            if resp.status_code >= 400:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text[:500]
                logger.warning("OpenRouter screenplay_to_json %s: %s", resp.status_code, err_body)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("screenplay_to_json: HTTP error %s", e)
        raise ValueError(f"API request failed: {e.response.status_code}") from e
    except Exception as e:
        logger.warning("screenplay_to_json: %s", e)
        raise ValueError(f"Request failed: {e!s}") from e

    content = None
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content") or msg.get("text")
        if content:
            break

    if not content:
        raise ValueError("No content in API response")

    raw_json = _extract_json_from_content(content)
    if not raw_json:
        raise ValueError("Could not extract JSON from response")

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        logger.warning("screenplay_to_json: JSON parse error %s", e)
        raise ValueError(f"Invalid JSON from model: {e!s}") from e
