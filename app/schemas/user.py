from pydantic import BaseModel, UUID4, EmailStr, Field
from datetime import datetime
from typing import Optional, Dict, List
from .log import LogResponse

class UserBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    timezone: str = 'UTC'
    locale: str = 'en-US'
    privacy_tier: str = 'local_only'
    daily_word_goal: int = 750
    writing_reminder_time: Optional[str] = None  # HH:MM in UTC
    theme_preferences: Optional[Dict] = None
    ai_features_enabled: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: Optional[str] = None
    timezone: str = 'UTC'
    locale: str = 'en-US'
    privacy_tier: str = 'local_only'
    daily_word_goal: int = 750
    writing_reminder_time: Optional[str] = None
    theme_preferences: Optional[Dict] = None
    ai_features_enabled: bool = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    display_name: Optional[str] = None
    timezone: Optional[str] = None
    locale: Optional[str] = None
    privacy_tier: Optional[str] = None
    daily_word_goal: Optional[int] = None
    writing_reminder_time: Optional[str] = None
    theme_preferences: Optional[Dict] = None
    ai_features_enabled: Optional[bool] = None
    password: Optional[str] = None

class User(UserBase):
    id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserResponse(User):
    logs_count: int = 0
    writing_streak: int = 0
    total_words_written: int = 0

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: str
    email: Optional[str] = None

class WritingSessionBase(BaseModel):
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    interruption_count: int = 0
    focus_score: Optional[float] = None

class WritingSession(WritingSessionBase):
    id: UUID4
    user_id: UUID4
    logs: List[LogResponse]

    class Config:
        from_attributes = True

class PromptBase(BaseModel):
    prompt_text: str
    prompt_type: str
    generation_context: Optional[Dict] = None

class Prompt(PromptBase):
    id: UUID4
    user_id: UUID4
    effectiveness_score: float = 0.0
    usage_count: int = 0
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserInsightBase(BaseModel):
    insight_type: str
    insight_data: Dict
    date_range_start: datetime
    date_range_end: datetime
    confidence_score: Optional[float] = None
    status: str = 'new'

class UserInsight(UserInsightBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True 