from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import List, Optional

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

class LogUpdate(BaseModel):
    content: str
    mood_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    completion_status: Optional[str] = None
    target_word_count: Optional[int] = None
    writing_duration: Optional[int] = None
    tags: List[str] = []  # List of tag names
    session_id: Optional[UUID4] = None
    prompt_id: Optional[UUID4] = None

class LogResponse(LogBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    word_count: Optional[int]
    processing_status: Optional[str]
    tags: List[Tag]

    class Config:
        from_attributes = True 