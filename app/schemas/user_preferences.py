from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from datetime import datetime

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
    writing_reminder_time: Optional[str] = None
    theme_preferences: Optional[Dict[str, Any]] = None
    ai_features_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None

class PrivacyTierUpdate(BaseModel):
    privacy_tier: Literal['local_only', 'analytics_sync', 'full_sync']
    consent_timestamp: datetime
    he_public_key: Optional[str] = None

class PrivacySettings(BaseModel):
    current_tier: str
    sync_enabled: bool
    sync_enabled_at: Optional[datetime]
    features_available: dict

    class Config:
        from_attributes = True 