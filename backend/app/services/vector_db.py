from qdrant_client import QdrantClient, models
from qdrant_client.models import Filter, FieldCondition, MatchValue
from app.core.config import settings
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Qwen3-Embedding-8B dimension (must match OpenRouter embedding size)
VECTOR_SIZE = getattr(settings, "EMBEDDING_DIMENSION", 4096)

# Payload keys used in filters; Qdrant requires a keyword index for each
FILTER_PAYLOAD_KEYS = ("scene_id", "location", "time_of_day", "int_ext", "actors")


class VectorDBService:
    def __init__(self):
        logger.info(f"Connecting to Qdrant at: {settings.QDRANT_URL}")
        if not settings.QDRANT_API_KEY:
            logger.warning("No Qdrant API Key provided (fine for local Qdrant).")

        client_kwargs = {"url": settings.QDRANT_URL, "check_compatibility": False}
        if settings.QDRANT_API_KEY:
            client_kwargs["api_key"] = settings.QDRANT_API_KEY
        timeout = getattr(settings, "QDRANT_TIMEOUT", 120)
        client_kwargs["timeout"] = timeout
        self.client = QdrantClient(**client_kwargs)
        self.collection_name = settings.COLLECTION_NAME

        try:
            if not self.client.collection_exists(self.collection_name):
                logger.info(f"Collection {self.collection_name} not found, creating (size={VECTOR_SIZE})...")
                self._create_collection()
            else:
                self._ensure_payload_indexes()
        except Exception as e:
            logger.error(f"Failed to check/create collection. Error: {e}")
            raise

    def _create_collection(self) -> None:
        """Create collection and payload indexes for filter fields."""
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )
        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        """Create keyword payload indexes for filter fields so Qdrant can filter on them."""
        for field_name in FILTER_PAYLOAD_KEYS:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema="keyword",
                )
                logger.info("Created payload index for field %r.", field_name)
            except Exception as e:
                # Index may already exist (e.g. "already exists" or 400)
                if "already" in str(e).lower() or "exists" in str(e).lower():
                    logger.debug("Payload index for %r already exists: %s", field_name, e)
                else:
                    logger.warning("Could not create payload index for %r: %s", field_name, e)

    def recreate_collection(self):
        """Delete and recreate the collection (e.g. before full re-index)."""
        try:
            logger.info("Recreating collection...")
            self.client.delete_collection(self.collection_name)
            self._create_collection()
            logger.info("Collection recreated successfully.")
        except Exception as e:
            logger.error(f"Error recreating collection: {e}")
            raise

    def add_segments(self, segments: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        """Upsert clip segments and their embeddings. Batched to avoid timeout on large payloads."""
        points = []
        for i, seg in enumerate(segments):
            payload = {k: v for k, v in seg.items() if k != "id"}
            points.append(
                models.PointStruct(
                    id=seg["id"],
                    vector=embeddings[i],
                    payload=payload,
                )
            )
        batch_size = 15
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=self.collection_name, points=batch)
            logger.info("Upserted batch %d–%d of %d.", i + 1, min(i + batch_size, len(points)), len(points))
        logger.info("Added %d segments to Qdrant.", len(segments))

    def _field_conditions(self, clause: Dict[str, Any], mode: str) -> List[Any]:
        """Build list of Qdrant conditions from a clause dict. mode: 'and' (each value AND), 'or' (each list → OR), 'not' (exclude)."""
        conditions = []
        scalar_keys = ("scene_id", "location", "time_of_day", "int_ext")
        for key in scalar_keys:
            v = clause.get(key)
            if v is None or v == "":
                continue
            if isinstance(v, list):
                vals = [str(x).strip() for x in v if x]
                if not vals:
                    continue
                # List: OR = "match any of these"; NOT = "match none of these"
                if mode == "or":
                    conditions.append(Filter(should=[FieldCondition(key=key, match=MatchValue(value=x)) for x in vals]))
                elif mode == "not":
                    conditions.extend([FieldCondition(key=key, match=MatchValue(value=x)) for x in vals])
                else:
                    # must with list = "match any of these" (one condition)
                    conditions.append(Filter(should=[FieldCondition(key=key, match=MatchValue(value=x)) for x in vals]))
            else:
                val = str(v).strip()
                if val:
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
        actors = clause.get("actors")
        if actors and isinstance(actors, list):
            actors = [str(a).strip() for a in actors if a]
        if actors:
            if mode == "or":
                conditions.append(Filter(should=[FieldCondition(key="actors", match=MatchValue(value=a)) for a in actors]))
            elif mode == "not":
                conditions.extend([FieldCondition(key="actors", match=MatchValue(value=a)) for a in actors])
            else:
                # AND: clip must involve all these actors
                conditions.extend([FieldCondition(key="actors", match=MatchValue(value=a)) for a in actors])
        return conditions

    def _build_filter(self, filters: Dict[str, Any]) -> Optional[Filter]:
        """Build Qdrant Filter with AND / OR / NOR support.

        Accepts either:
        - Structured: {"must": {...}, "should": {...}, "must_not": {...}}
          - must: ALL conditions (AND)
          - should: at least ONE condition (OR)
          - must_not: NONE of these (NOR)
        - Legacy flat dict: treated as must (AND), with actors = OR within that key.
        """
        must_list = []
        should_list = []
        must_not_list = []

        if not filters:
            return None

        # Structured form: must / should / must_not
        if "must" in filters or "should" in filters or "must_not" in filters:
            m = filters.get("must") or {}
            if isinstance(m, dict):
                must_list = self._field_conditions(m, "and")
            s = filters.get("should") or {}
            if isinstance(s, dict):
                # Each key in should → at least one match; combine into one big OR
                for key in ("scene_id", "location", "time_of_day", "int_ext", "actors"):
                    v = s.get(key)
                    if v is None or v == "":
                        continue
                    if key == "actors" and isinstance(v, list):
                        v = [str(a).strip() for a in v if a]
                        if v:
                            should_list.append(Filter(should=[FieldCondition(key="actors", match=MatchValue(value=a)) for a in v]))
                    elif key in ("scene_id", "location", "time_of_day", "int_ext"):
                        if isinstance(v, list):
                            for x in v:
                                if x:
                                    should_list.append(FieldCondition(key=key, match=MatchValue(value=str(x).strip())))
                        else:
                            should_list.append(FieldCondition(key=key, match=MatchValue(value=str(v).strip())))
            n = filters.get("must_not") or {}
            if isinstance(n, dict):
                must_not_list = self._field_conditions(n, "not")
        else:
            # Legacy flat: all AND, actors = OR
            if filters.get("scene_id"):
                must_list.append(FieldCondition(key="scene_id", match=MatchValue(value=str(filters["scene_id"]).strip())))
            if filters.get("location"):
                must_list.append(FieldCondition(key="location", match=MatchValue(value=str(filters["location"]).strip())))
            if filters.get("time_of_day"):
                must_list.append(FieldCondition(key="time_of_day", match=MatchValue(value=str(filters["time_of_day"]).strip())))
            if filters.get("int_ext"):
                must_list.append(FieldCondition(key="int_ext", match=MatchValue(value=str(filters["int_ext"]).strip())))
            actors = filters.get("actors")
            if actors and isinstance(actors, list) and len(actors) > 0:
                actor_conditions = [FieldCondition(key="actors", match=MatchValue(value=str(a).strip())) for a in actors if a]
                if actor_conditions:
                    must_list.append(Filter(should=actor_conditions))

        if not must_list and not should_list and not must_not_list:
            return None
        kwargs = {}
        if must_list:
            kwargs["must"] = must_list
        if should_list:
            kwargs["should"] = should_list
        if must_not_list:
            kwargs["must_not"] = must_not_list
        return Filter(**kwargs)

    def search(self, query_embedding: List[float], n_results: int = 20, filters: Optional[Dict[str, Any]] = None):
        """Nearest-neighbor search. Optionally restrict by metadata (scene_id, location, time_of_day, int_ext, actors)."""
        query_filter = self._build_filter(filters) if filters else None
        if query_filter:
            logger.info("vector_db.search: applying metadata filter %s", filters)
        logger.info("vector_db.search: collection=%s, n_results=%d, query_vector_len=%d", self.collection_name, n_results, len(query_embedding))
        kwargs = dict(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=n_results,
            with_payload=True,
            with_vectors=False,
        )
        if query_filter is not None:
            # Qdrant client expects "query_filter" (not "filter")
            kwargs["query_filter"] = query_filter
        response = self.client.query_points(**kwargs)
        points = response.points or []
        logger.info("vector_db.search: returned %d points.", len(points))
        return points


vector_db = VectorDBService()
