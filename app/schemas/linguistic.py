from pydantic import BaseModel, UUID4
from typing import List, Dict, Any, Optional
from datetime import datetime

class EmotionScores(BaseModel):
    emotions: Dict[str, float]
    subjectivity: float

class WritingStyleMetrics(BaseModel):
    sentence_types: Dict[str, float]
    style_similarities: Optional[Dict[str, float]] = None
    formality_indicators: Optional[Dict[str, float]] = None

class TextAnalysis(BaseModel):
    vocabulary_diversity_score: float
    sentiment_score: float
    complexity_score: float
    readability_level: float
    emotion_scores: EmotionScores
    writing_style_metrics: WritingStyleMetrics

class LinguisticMetricsResponse(BaseModel):
    id: Optional[UUID4] = None
    log_id: UUID4
    vocabulary_diversity_score: float
    sentiment_score: float
    complexity_score: float
    readability_level: float
    emotion_scores: EmotionScores
    writing_style_metrics: WritingStyleMetrics
    processed_at: datetime

    class Config:
        from_attributes = True 