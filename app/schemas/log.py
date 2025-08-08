from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import List, Optional, Dict

class TagBase(BaseModel):
    name: str
    color: Optional[str] = None

class TagCreate(TagBase):
    id: UUID4
    created_at: datetime

class Tag(TagBase):
    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class ThemeBase(BaseModel):
    name: str
    description: Optional[str] = None
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class Theme(ThemeBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime  # Add the missing updated_at field
    confidence_score: float = Field(ge=0.0, le=1.0)
    detected_at: datetime

    class Config:
        from_attributes = True

class LinguisticMetricsBase(BaseModel):
    vocabulary_diversity_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    complexity_score: Optional[float] = None
    readability_level: Optional[float] = None
    emotion_scores: Optional[Dict] = None
    writing_style_metrics: Optional[Dict] = None

class LinguisticMetrics(LinguisticMetricsBase):
    id: UUID4
    log_id: UUID4
    processed_at: datetime

    class Config:
        from_attributes = True

class EntryRevisionBase(BaseModel):
    revision_number: int
    content_delta: Dict
    revision_type: str

class EntryRevision(EntryRevisionBase):
    id: UUID4
    log_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class LogBase(BaseModel):
    content: str
    mood_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    completion_status: Optional[str] = 'draft'
    target_word_count: Optional[int] = 750
    writing_duration: Optional[int] = None

class LogCreate(LogBase):
    id: UUID4  # Client must provide the ID
    tags: List[str] = []  # List of tag names
    session_id: Optional[UUID4] = None
    prompt_id: Optional[UUID4] = None

class LogUpdate(LogBase):
    id: UUID4  # Required for updates
    tags: List[str] = []  # List of tag names
    session_id: Optional[UUID4] = None
    prompt_id: Optional[UUID4] = None

class LogResponse(LogBase):
    id: UUID4
    user_id: UUID4
    weaviate_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    word_count: Optional[int]
    processing_status: Optional[str]
    tags: List[Tag]
    themes: List[Theme]
    linguistic_metrics: Optional[LinguisticMetrics]
    revisions: List[EntryRevision]

    class Config:
        from_attributes = True 