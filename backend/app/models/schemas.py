from pydantic import BaseModel, field_validator
from typing import List, Optional, Any, Union

from app.core.utils import timestamp_to_seconds


class Dialogue(BaseModel):
    timestamp_start_sec: float = 0.0
    timestamp_end_sec: float = 0.0
    actor: str
    text: str
    actor_context: Optional[str] = None
    delivery: Optional[str] = None
    actual_dialogs: Optional[List[str]] = None

    @field_validator("timestamp_start_sec", "timestamp_end_sec", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Union[str, float, None]) -> float:
        if v is None:
            return 0.0
        return timestamp_to_seconds(v)

class Clip(BaseModel):
    clip_id: str
    clip_description: List[str]
    actors_involved: List[str]
    dialogue: List[Dialogue] = []
    # Used when dialogue is empty (clips without spoken lines)
    estimated_clip_start: Optional[Union[str, float]] = None
    estimated_clip_end: Optional[Union[str, float]] = None

class SceneDescription(BaseModel):
    int_ext: str
    location: str
    time_of_day: str
    actors_involved: List[str]

class Scene(BaseModel):
    scene_id: str
    scene_description: SceneDescription
    clips: List[Clip]

class SearchRequest(BaseModel):
    query: str
    limit: int = 10  # Max 20 per problem statement (scope constraint)
    # Optional metadata filters (pre-retrieval in vector DB; §2.3 IMPLEMENTATION_PLAN)
    scene_id: Optional[str] = None
    location: Optional[str] = None
    time_of_day: Optional[str] = None
    int_ext: Optional[str] = None
    actors: Optional[List[str]] = None  # Clips where at least one of these actors is involved

    @field_validator("limit")
    @classmethod
    def limit_max_20(cls, v: int) -> int:
        return min(max(1, v), 20)

class SearchResult(BaseModel):
    clip_id: str
    video_id: Optional[str] = None  # Keeping for compatibility if needed, though clip_id is primary
    start: float
    end: float
    text: str
    score: float  # Raw reranker relevance score
    match_score: float = 0.0  # Normalized 0–1 (best result in batch = 1.0), always present
    confidence: Optional[str] = None
    metadata: Optional[Any] = None

class IndexRequest(BaseModel):
    scenes: List[Scene]
    recreate_collection: bool = False
