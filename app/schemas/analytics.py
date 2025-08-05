from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional, Dict, List

class ThemeBase(BaseModel):
    name: str
    description: Optional[str] = None
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

class ThemeCreate(ThemeBase):
    pass

class ThemeUpdate(ThemeBase):
    pass

class Theme(ThemeBase):
    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class ThemeAssignment(BaseModel):
    theme_id: UUID4
    log_id: UUID4
    confidence_score: float = Field(ge=0.0, le=1.0)
    detected_at: datetime

    class Config:
        from_attributes = True

class LinguisticMetricsBase(BaseModel):
    vocabulary_diversity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    complexity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    readability_level: Optional[float] = None
    emotion_scores: Optional[Dict[str, float]] = None
    writing_style_metrics: Optional[Dict[str, float]] = None

class LinguisticMetricsCreate(LinguisticMetricsBase):
    log_id: UUID4

class LinguisticMetricsUpdate(LinguisticMetricsBase):
    pass

class LinguisticMetrics(LinguisticMetricsBase):
    id: UUID4
    log_id: UUID4
    processed_at: datetime

    class Config:
        from_attributes = True

class WritingAnalytics(BaseModel):
    total_words: int
    average_words_per_entry: float
    writing_streak: int
    total_entries: int
    completion_rate: float
    average_sentiment: float
    common_themes: List[Theme]
    vocabulary_growth: Dict[str, float]
    writing_patterns: Dict[str, any]

    class Config:
        from_attributes = True 