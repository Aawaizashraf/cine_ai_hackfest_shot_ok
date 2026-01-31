# Example Search Queries

Use these with **POST /api/v1/search** or **POST /api/v1/search/stream** (`{"query": "...", "limit": 10}`) to exercise the full pipeline: query understanding, filters (AND/OR/NOR), hybrid retrieval, fallback, and rerank.

---

## Semantic only (no filters)

LLM may return empty `filters`; search runs on intent only.

| Query | What it exercises |
|-------|--------------------|
| `someone asking for justice` | Intent parsing, semantic + rerank |
| `Don Corleone refusing a request` | Intent, no metadata filter |
| `tense conversation in an office` | Semantic match on location/atmosphere |
| `character weeping while speaking` | Pure semantic / dialogue match |

---

## Filters: **must** (AND)

LLM returns `filters.must`; all conditions must match.

| Query | Expected filter | What it exercises |
|-------|-----------------|--------------------|
| `Don Corleone in his office during the day` | `must: { location: "DON'S OFFICE", time_of_day: "DAY", actors: ["DON CORLEONE"] }` | location + time_of_day + actors (AND) |
| `Bonasera in Don's office` | `must: { location: "DON'S OFFICE", actors: ["BONASERA"] }` | location + actor |
| `wedding party scenes` | `must: { location: "WEDDING PARTY (SUMMER 1945)" }` or similar | location only |
| `scene 1 only` | `must: { scene_id: "scene_1" }` | scene_id filter |

---

## Filters: **should** (OR)

LLM returns `filters.should`; at least one condition must match.

| Query | Expected filter | What it exercises |
|-------|-----------------|--------------------|
| `Don Corleone or Sonny` | `should: { actors: ["DON CORLEONE", "SONNY"] }` | actors OR |
| `scene 1 or scene 2` | `should: { scene_id: ["scene_1", "scene_2"] }` | scene_id OR |
| `office or mall` | `should: { location: ["DON'S OFFICE", "MALL"] }` | location OR |

---

## Filters: **must_not** (NOR)

LLM returns `filters.must_not`; none of these must match.

| Query | Expected filter | What it exercises |
|-------|-----------------|--------------------|
| `not at night` | `must_not: { time_of_day: "NIGHT" }` | time_of_day NOR |
| `without Michael` | `must_not: { actors: ["MICHAEL"] }` | actors NOR |
| `not in the mall` | `must_not: { location: "MALL" }` | location NOR |
| `interior only` | `must: { int_ext: "INT" }` (or must_not EXT) | int_ext |

---

## Combined filters

| Query | Expected filter | What it exercises |
|-------|-----------------|--------------------|
| `Don's office but not at night` | `must: { location: "DON'S OFFICE" }, must_not: { time_of_day: "NIGHT" }` | must + must_not |
| `exterior daytime scenes` | `must: { int_ext: "EXT", time_of_day: "DAY" }` | int_ext + time_of_day |

---

## Hybrid retrieval

Query where the LLM rewrites intent so it differs from the raw query → second vector search with raw query + RRF merge.

| Query | What it exercises |
|-------|--------------------|
| `hesitant to answer` | Intent e.g. "person showing hesitation while answering" → hybrid with raw "hesitant to answer" |
| `when does Bonasera ask for justice` | Intent rewrite → hybrid |
| `wedding scenes` | Intent may be "wedding scenes at the wedding party" → hybrid if different from raw |

---

## Filter fallback

Strict filter returns &lt; 5 candidates → backend retries without filter and merges (up to 5+ results).

| Query | What it exercises |
|-------|--------------------|
| `wedding scenes at the mall with Don and Sonny` | May filter to MALL + actors → few clips → fallback unfiltered + merge |
| `scene 5 with Michael and Kay` | Very narrow → may trigger fallback |

---

## Quick copy-paste list

```
someone asking for justice
Don Corleone in his office during the day
Bonasera in Don's office
wedding party scenes
scene 1 only
Don Corleone or Sonny
scene 1 or scene 2
not at night
without Michael
Don's office but not at night
hesitant to answer
wedding scenes
```

Use any of these in the frontend search box or via:

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Don Corleone in his office", "limit": 5}'
```

Streaming:

```bash
curl -X POST http://localhost:8000/api/v1/search/stream \
  -H "Content-Type: application/json" \
  -d '{"query": "wedding scenes", "limit": 5}' \
  -N
```
