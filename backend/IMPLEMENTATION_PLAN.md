# Detailed Implementation Plan: Semantic Clip Search + UI

## Goal
- **Input:** User query (natural language, e.g. “When does Bonasera ask for justice?” or “Don Corleone’s office scene”).
- **Output:** Relevant clips from *The Godfather* (1972), with timestamps and context.
- **UI:** Search box + display of relevant clips (with optional video playback at the right time).

---

## 1. Data Overview

| File | Role |
|------|------|
| **the_godfather_20scenes_with_actual_dialogs.json** | **Primary source.** Scenes → clips → dialogue with `timestamp_start_sec`, `timestamp_end_sec`, `clip_description`, `actors_involved`, `text`, `actual_dialogs`. Use this for both embedding and UI. |
| **the_godfather_20scenes.json** | Same structure, no `actual_dialogs`. Fallback only if you want lighter data. |
| **The.Godfather.1972...YIFY.json** | Subtitle-level lines (start/end/text). Useful for fine-grained timestamps or aligning with SRT if needed. |
| **The.Godfather.1972...YIFY.mp4** | Movie file for playback. Path: `The Godfather (1972) [1080p]/The.Godfather.1972.1080p.BrRip.x264.BOKUTOX.YIFY.mp4` |

**Recommendation:** Use **the_godfather_20scenes_with_actual_dialogs.json** as the single source of truth for “clips” and timestamps.

---

## 2. Embed vs Metadata vs Filter

**Unit = one clip** (e.g. `scene_1_clip_1`). Below: what goes into the embedding, what you store/return as metadata, and what you use for pre-retrieval filtering.

### 2.1 Fields to **EMBED** (semantic search text)

These go into the **single text blob** you pass to the embedding model. Only semantic content—no IDs or raw timestamps.

| Source | Field(s) | Why |
|--------|----------|-----|
| **scene_description** | `location` | Matches “Don’s office”, “hospital”, etc. |
| **scene_description** | `time_of_day` | Matches “day”, “night” |
| **scene_description** | `actors_involved` | Matches “Bonasera”, “Don Corleone” |
| **clip** | `clip_description` (all strings, joined) | Visual/action context (“whispers into the DON’s ear”, “we see the office”) |
| **dialogue[]** | `actor` + `text` | Main signal for “when does X say Y” |
| **dialogue[]** (optional) | `actual_dialogs` (joined) | Closer to spoken lines; can add if you want stronger dialogue match |

**Do NOT embed:** `clip_id`, `scene_id`, timestamps, `int_ext` (use these as metadata/filter only).

**Example `search_text` for one clip:**  
`"DON'S OFFICE DAY BONASERA DON CORLEONE By now the view is full and we see Don Corleone's office... DON CORLEONE: Bonasera we know each other for years... BONASERA: What do you want of me?..."`

---

### 2.2 Fields to keep as **METADATA** (stored with vector, returned in API, used in UI)

Stored alongside the embedding and returned with each hit. Used for display and for *post*-retrieval filtering (or filter-in-vector-DB if your store supports it).

| Field | Source | Use |
|-------|--------|-----|
| **clip_id** | clip | Unique id, playback key |
| **scene_id** | scene | Grouping, “Scene 1” label |
| **start_sec** | computed from `dialogue[].timestamp_start_sec` | Video seek (e.g. `video.currentTime`) |
| **end_sec** | computed from `dialogue[].timestamp_end_sec` | Optional: pause at end of clip |
| **start_display** / **end_display** | same, formatted as "MM:SS" or "HH:MM:SS" | Shown on clip card |
| **location** | scene_description.location | e.g. “DON'S OFFICE” |
| **time_of_day** | scene_description.time_of_day | e.g. “DAY” |
| **actors_involved** | clip.actors_involved (or scene) | Display “BONASERA, DON CORLEONE” |
| **snippet** | first 1–2 dialogue lines or first part of clip_description | Preview text on card |
| **int_ext** | scene_description.int_ext | Optional: “INT” / “EXT” |

You can add more display fields (e.g. first dialogue line only) as needed; keep them out of the embedded text.

---

### 2.3 Fields to use for **FILTERING** (before or during retrieval)

Use these to restrict *which* clips are eligible before (or while) you run vector search. Reduces candidates and focuses results.

| Filter | Source | Example filter |
|--------|--------|----------------|
| **actor / actors_involved** | clip.actors_involved or scene_description.actors_involved | “Only clips with DON CORLEONE” |
| **scene_id** | scene | “Only scene_1” |
| **location** | scene_description.location | “Only DON'S OFFICE” |
| **time_of_day** | scene_description.time_of_day | “Only NIGHT” |
| **int_ext** | scene_description.int_ext | “Only INTERIOR” |

**How to use:**

- **Pre-retrieval:** If the user (or UI) says “clips with Don Corleone”, filter clips where `"DON CORLEONE" in actors_involved`, then embed the query and search only within that subset.
- **Vector DB:** If using Chroma/Qdrant/etc., store `actors_involved`, `location`, `scene_id` as metadata and use `where` / filter expressions in the query.
- **Post-retrieval:** Run vector search first, then drop results that don’t match the filter (simpler but less efficient if the filter is strict).

**Recommendation:** For a hackathon, **metadata** = what you need for display + playback. **Filter** = only add actor/scene/location filters if you have UI controls or parsed query intent (e.g. “clips with Michael” → filter by actor).

---

## 3. Searchable Unit: Building the Embed Text

For each clip, build the **single text blob** to embed as in **§2.1** (location, time_of_day, actors, clip_description, dialogue actor+text). Store **§2.2** as metadata. Use **§2.3** only when you have explicit filter criteria.

---

## 4. Embedding & Retrieval Pipeline

### 4.1 Text preparation (per clip)

1. Load `the_godfather_20scenes_with_actual_dialogs.json`.
2. For each scene → each clip:
   - Collect: scene location, time_of_day, scene actors.
   - Clip description lines (joined).
   - For each dialogue: `actor: text` (and optionally actual_dialogs).
   - Compute clip time range: e.g. `start = min(dialogue.timestamp_start_sec)`, `end = max(dialogue.timestamp_end_sec)` (convert "00:04:25,260" → seconds for storage and playback).
3. Store one record per clip, e.g.:
   - `clip_id`, `scene_id`, `start_sec`, `end_sec`, `display_title` (e.g. scene + location), `search_text` (the blob you embed), plus any extra fields for the UI (actors, first line of dialogue, etc.).

### 4.2 Embedding model

- **Option A (local, free):** `sentence-transformers` (e.g. `all-MiniLM-L6-v2` or `all-mpnet-base-v2`). Good for “meaning” similarity.
- **Option B (API):** OpenAI `text-embedding-3-small` or similar. Same idea: embed `search_text` and the query.

### 4.3 Vector store

- **Simple (hackathon):** Precompute embeddings for all clips, store in **NumPy** (vectors) + **JSON/pandas** (metadata). At query time: embed query, cosine similarity, argsort, return top-k.
- **Scalable:** **Chroma**, **FAISS**, or **Qdrant**. Index by `clip_id`; metadata (start_sec, end_sec, scene_id, snippet) in the index for filtering/display.

### 4.4 Retrieval

1. User sends query string.
2. Embed query with same model used for clips.
3. Search vector store (cosine or inner product), get top-k (e.g. k=5–10).
4. Return list of clips with: `clip_id`, `scene_id`, `start_sec`, `end_sec`, `snippet` (e.g. first 100 chars of dialogue or clip_description), `score` (optional), and any other UI fields.

---

## 5. Backend API

- **Framework:** FastAPI (or Flask).
- **Endpoints:**
  1. **GET /api/clips/search?q=...**  
     - Embeds `q`, runs retrieval, returns JSON list of clip results (with timestamps in seconds and human-readable form).
  2. **GET /api/clips** (optional)  
     - Return all clips or list of scene/clip IDs for debugging.
  3. **GET /api/video** or **GET /api/movie** (optional)  
     - Return video URL or path so the frontend can load the movie (e.g. `/static/movie.mp4` or a stable path the UI knows).

- **Startup:** On app start, load the precomputed index (vectors + metadata) or build it once and cache (e.g. pickle/NumPy/Chroma persist).

- **CORS:** Enable if frontend is on a different port (e.g. React/Vite dev server).

---

## 6. Frontend UI

### 6.1 Layout

- **Header:** Title, e.g. “The Godfather – Clip Search”.
- **Search:** Single input + “Search” button (or search-on-enter). Call `GET /api/clips/search?q=...`.
- **Results:** List or grid of **clip cards**.

### 6.2 Each clip card

- **Scene / location** (from scene_description).
- **Clip identifier** (e.g. “Scene 1, Clip 4” or clip_id).
- **Time range:** e.g. “04:25 – 04:47” (from `start_sec` / `end_sec`).
- **Snippet:** One or two lines of dialogue or clip description.
- **“Play” control:** Either:
  - **A)** Open the full movie in a video player (HTML5 `<video>`) and set `currentTime = start_sec` (and optionally `end` via logic or `timeupdate`), or  
  - **B)** Link to the movie with a time hash, e.g. `movie.mp4#t=265` (265 seconds), if your player supports it.

### 6.3 Video playback

- **Option A – Single full movie:**  
  - One `<video src="/path/to/Godfather.mp4">`.  
  - On “Play” for a clip: `video.currentTime = start_sec`; optionally listen to `timeupdate` and pause at `end_sec` to simulate “clip.”
- **Option B – Pre-cut clips (optional):**  
  - Use ffmpeg to export short clips per clip_id (e.g. `ffmpeg -ss start -to end -i movie.mp4 -c copy clip_1.mp4`).  
  - UI shows `<video src="/clips/clip_1.mp4">`. Better UX but more storage and preprocessing.

Recommendation for a hackathon: **Option A** (single movie + seek to `start_sec`).

### 6.4 Tech stack (suggested)

- **React** (or Next.js) or **Vue** + **Vite**.
- **Fetch** or **axios** to call `/api/clips/search?q=...`.
- **CSS/Tailwind** for cards and layout.

---

## 7. Implementation Order

| Step | Task | Output |
|------|------|--------|
| 1 | Parse `the_godfather_20scenes_with_actual_dialogs.json`, build per-clip records (search_text + start_sec/end_sec, scene_id, clip_id, snippet). | Script: `build_clip_index.py` → `clips.json` or similar. |
| 2 | Add embedding: same script or `embed_clips.py` → compute vectors, save (e.g. `embeddings.npy` + `clip_metadata.json`). | Vector index + metadata. |
| 3 | Implement retrieval: given query string, embed → similarity → top-k. | Function `search_clips(query, k=10)`. |
| 4 | Expose FastAPI: load index on startup, implement `GET /api/clips/search?q=...`. | Backend running locally. |
| 5 | Build minimal UI: search box + results list with time and snippet. | Frontend calling API. |
| 6 | Add video: serve movie (or a copy) under `/static` or similar; in UI, `<video>` + “Play” sets `currentTime = start_sec`. | Full flow: query → clips → play at time. |
| 7 | (Optional) Pre-extract clips with ffmpeg; UI links to clip files. | Better “clip” experience. |

---

## 8. Helpful Snippets

### 8.1 Timestamp conversion (JSON → seconds)

```python
def timestamp_to_seconds(ts: str) -> float:
    # "00:04:25,260" -> 265.26
    from datetime import datetime
    ts = ts.replace(",", ".")
    pt = datetime.strptime(ts, "%H:%M:%S.%f")
    return pt.hour * 3600 + pt.minute * 60 + pt.second + pt.microsecond / 1e6
```

### 8.2 Building search_text for one clip

```python
def clip_to_search_text(scene_desc, clip) -> str:
    parts = [
        scene_desc.get("location", ""),
        scene_desc.get("time_of_day", ""),
        " ".join(scene_desc.get("actors_involved", [])),
        " ".join(clip.get("clip_description", [])),
    ]
    for d in clip.get("dialogue", []):
        parts.append(f"{d.get('actor', '')}: {d.get('text', '')}")
    return " ".join(parts)
```

---

## 9. File Structure Suggestion

```
cine_ai_hackathon/
├── data/
│   ├── the_godfather_20scenes_with_actual_dialogs.json   # input
│   ├── clip_metadata.json                                 # built: id, start_sec, end_sec, snippet, scene_id
│   └── embeddings.npy                                     # built: (N, dim) or use Chroma/FAISS
├── backend/
│   ├── main.py                                            # FastAPI app, /api/clips/search
│   ├── index_builder.py                                   # build clip_metadata + embeddings
│   └── retrieval.py                                       # search_clips(query, k)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── SearchBar.jsx
│   │   │   ├── ClipCard.jsx
│   │   │   └── VideoPlayer.jsx
│   └── ...
├── The Godfather (1972) [1080p]/
│   └── *.mp4
└── IMPLEMENTATION_PLAN.md (this file)
```

---

## 10. Summary

- **Data:** Use **the_godfather_20scenes_with_actual_dialogs.json**; one searchable unit = one **clip** (scene + clip description + dialogue).
- **Embed:** Concatenate location, time, actors, clip description, and dialogue into `search_text`; embed with sentence-transformers or OpenAI.
- **Retrieve:** Vector similarity (cosine) → top-k clips; return clip_id, start_sec, end_sec, snippet.
- **Backend:** FastAPI with `/api/clips/search?q=...` and optional video URL.
- **UI:** Search input → clip cards (scene, time range, snippet) + “Play” that seeks the main movie to `start_sec`.

Following this plan gives you end-to-end: **user query → relevant clips with timestamps → display and optional playback** in the UI.
