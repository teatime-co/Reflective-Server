from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime

class ThemeBase(BaseModel):
    name: str
    description: Optional[str] = None

class ThemeResponse(ThemeBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ThemeWithLogsResponse(ThemeResponse):
    log_count: int
    last_used: Optional[datetime] = None

class ThemeMatch(BaseModel):
    theme: ThemeResponse
    confidence_score: float

class ThemeSuggestion(BaseModel):
    suggested_themes: List[str] 