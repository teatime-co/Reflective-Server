from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserPreferencesResponse(BaseModel):
    daily_word_goal: int
    writing_reminder_time: Optional[str] = None  # HH:MM format
    theme_preferences: Optional[Dict[str, Any]] = None
    ai_features_enabled: bool = True
    timezone: str
    locale: str

    class Config:
        from_attributes = True

class UserPreferencesUpdate(BaseModel):
    daily_word_goal: Optional[int] = None
    writing_reminder_time: Optional[str] = None  # HH:MM format
    theme_preferences: Optional[Dict[str, Any]] = None
    ai_features_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None 