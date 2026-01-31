"""
Parse user search query into intent + keywords + filters using OpenRouter chat.
Intent is used for semantic embedding; keywords for hybrid; filters (actors, location, etc.) for vector DB.
"""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Canonical filter values loaded from the 20-scenes JSON (lazy)
_canonical_filters: Optional[Dict[str, List[str]]] = None


def _load_canonical_filters() -> Dict[str, List[str]]:
    """Load unique scene_id, location, time_of_day, int_ext, and actor names from the film data."""
    global _canonical_filters
    if _canonical_filters is not None:
        return _canonical_filters
    path = getattr(settings, "GODFATHER_20_SCENES_JSON", None)
    if not path or not Path(path).exists():
        _canonical_filters = {
            "scene_id": [],
            "location": [],
            "time_of_day": ["DAY", "NIGHT"],
            "int_ext": ["INT", "EXT"],
            "actors": [],
        }
        return _canonical_filters
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning("Could not load canonical filters from %s: %s", path, e)
        _canonical_filters = {
            "scene_id": [],
            "location": [],
            "time_of_day": ["DAY", "NIGHT"],
            "int_ext": ["INT", "EXT"],
            "actors": [],
        }
        return _canonical_filters
    scene_ids = set()
    locations = set()
    time_of_day = set()
    int_ext = set()
    actors = set()
    for scene in data if isinstance(data, list) else []:
        scene_ids.add(scene.get("scene_id", ""))
        desc = scene.get("scene_description") or {}
        locations.add(desc.get("location", ""))
        time_of_day.add(desc.get("time_of_day", ""))
        int_ext.add(desc.get("int_ext", ""))
        for a in desc.get("actors_involved") or []:
            actors.add(a)
        for clip in scene.get("clips") or []:
            for a in clip.get("actors_involved") or []:
                actors.add(a)
    _canonical_filters = {
        "scene_id": sorted(s for s in scene_ids if s),
        "location": sorted(l for l in locations if l),
        "time_of_day": sorted(t for t in time_of_day if t),
        "int_ext": sorted(e for e in int_ext if e),
        "actors": sorted(a for a in actors if a),
    }
    logger.debug("Loaded canonical filters: %d locations, %d actors", len(_canonical_filters["location"]), len(_canonical_filters["actors"]))
    return _canonical_filters


@dataclass
class ParsedQuery:
    """Result of LLM query understanding."""
    intent: str          # Clear description for "Find footage that shows: {intent}"
    keywords: List[str]  # Optional phrases/words for hybrid or display
    filters: Dict[str, Any] = field(default_factory=dict)  # Optional: scene_id, location, time_of_day, int_ext, actors (from LLM)


def parse_query(raw_query: str) -> ParsedQuery:
    """
    Use LLM to turn raw query into intent (and keywords) for footage search.
    Falls back to raw_query as intent if API fails or key is missing.
    """
    if not raw_query or not raw_query.strip():
        logger.debug("parse_query: empty input, returning empty ParsedQuery.")
        return ParsedQuery(intent="", keywords=[], filters={})

    logger.info("parse_query: raw_query=%r", raw_query[:120] + ("..." if len(raw_query) > 120 else ""))
    if not settings.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set; using raw query as intent.")
        return ParsedQuery(intent=raw_query.strip(), keywords=[], filters={})

    canonical = _load_canonical_filters()
    locations_str = ", ".join(repr(s) for s in canonical["location"][:30])  # cap for prompt size
    actors_str = ", ".join(repr(s) for s in canonical["actors"][:40])
    scene_ids_str = ", ".join(canonical["scene_id"][:25])
    time_str = ", ".join(canonical["time_of_day"])
    int_ext_str = ", ".join(canonical["int_ext"])

    system = f"""You are a query understander for a film footage search engine (The Godfather). Editors describe what they want in natural language.

Your job: output a single JSON object with exactly these keys:
- "intent": one clear sentence describing what kind of footage to find (e.g. "someone refusing a request firmly", "tense conversation in an office"). Use the user's words but make it concrete and search-friendly. No preamble.
- "keywords": a short list of 0–5 important phrases or words from the query (e.g. ["justice", "Don Corleone"]). Can be empty [].
- "filters": optional metadata with AND / OR / NOR logic. Use ONLY these exact values (no other text). Allowed values:
  scene_id: {scene_ids_str}. location: {locations_str}. time_of_day: {time_str}. int_ext: {int_ext_str}. actors: {actors_str}.

  "filters" must be an object with up to three keys: "must", "should", "must_not". Each is an object with optional keys: scene_id, location, time_of_day, int_ext, actors (array). Omit a key entirely if not needed.

  - "must" (AND): ALL of these must match. Use when user says "in the office and during day", "with both Don and Sonny" (actors AND). Example: {{"must": {{"location": "DON'S OFFICE", "time_of_day": "DAY"}}}} or {{"must": {{"actors": ["DON CORLEONE", "SONNY"]}}}}.
  - "should" (OR): at least ONE must match. Use when user says "Don Corleone or Sonny", "scene 1 or scene 2", "office or mall". Example: {{"should": {{"actors": ["DON CORLEONE", "SONNY"]}}}} or {{"should": {{"scene_id": ["scene_1", "scene_2"]}}}}.
  - "must_not" (NOR): NONE of these must match. Use when user says "not at night", "without Michael", "not in the mall". Example: {{"must_not": {{"time_of_day": "NIGHT"}}}} or {{"must_not": {{"actors": ["MICHAEL"]}}}}.

  You can combine: {{"must": {{"location": "DON'S OFFICE"}}, "must_not": {{"time_of_day": "NIGHT"}}}}. If the user does not specify any filters, use {{}}.

Output only the JSON, no markdown or explanation."""

    logger.info("parse_query: calling OpenRouter chat (model=%s)...", getattr(settings, "OPENROUTER_CHAT_MODEL", "?"))
    try:
        with httpx.Client(timeout=15.0) as client:
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
                        {"role": "system", "content": system},
                        {"role": "user", "content": raw_query},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 256,
                },
            )
            if resp.status_code >= 400:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = resp.text[:500]
                logger.warning("OpenRouter chat %s: %s", resp.status_code, err_body)
            resp.raise_for_status()
            data = resp.json()
        logger.info("parse_query: OpenRouter response received.")
    except httpx.HTTPStatusError as e:
        logger.warning("Query understanding API failed: %s; using raw query as intent.", e)
        return ParsedQuery(intent=raw_query.strip(), keywords=[], filters={})
    except Exception as e:
        logger.warning("Query understanding API failed: %s; using raw query as intent.", e)
        return ParsedQuery(intent=raw_query.strip(), keywords=[], filters={})

    content = None
    for choice in data.get("choices", []):
        msg = choice.get("message", {})
        content = msg.get("content") or msg.get("text")
        if content:
            break
    if not content:
        logger.warning("parse_query: no content in OpenRouter choices; using raw query.")
        return ParsedQuery(intent=raw_query.strip(), keywords=[], filters={})

    content = content.strip()
    logger.debug("parse_query: raw content length=%d", len(content))
    # Strip markdown code block if present
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    try:
        obj = json.loads(content)
        intent = (obj.get("intent") or raw_query).strip() or raw_query.strip()
        kw = obj.get("keywords")
        keywords = list(kw) if isinstance(kw, list) else []
        keywords = [str(k).strip() for k in keywords if k]
        # Build filters for vector DB: support must / should / must_not (AND / OR / NOR)
        raw_filters = obj.get("filters") or {}
        filters = {}
        if isinstance(raw_filters, dict):
            for clause_key in ("must", "should", "must_not"):
                clause = raw_filters.get(clause_key)
                if not isinstance(clause, dict):
                    continue
                out = {}
                for key in ("scene_id", "location", "time_of_day", "int_ext"):
                    v = clause.get(key)
                    if v is None or v == "":
                        continue
                    if isinstance(v, list):
                        out[key] = [str(x).strip() for x in v if x]
                    else:
                        out[key] = str(v).strip()
                    if not out[key] or (isinstance(out[key], list) and not out[key]):
                        out.pop(key, None)
                af = clause.get("actors")
                if af and isinstance(af, list):
                    out["actors"] = [str(a).strip() for a in af if a]
                out = {k: v for k, v in out.items() if v}
                if out:
                    filters[clause_key] = out
        logger.info("parse_query: parsed intent=%r, keywords=%s, filters=%s", intent[:80] + ("..." if len(intent) > 80 else ""), keywords, filters)
        return ParsedQuery(intent=intent, keywords=keywords, filters=filters)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Query understanding parse failed: %s; using raw query as intent.", e)
        return ParsedQuery(intent=raw_query.strip(), keywords=[], filters={})
