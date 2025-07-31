from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List, Optional

class TagBase(BaseModel):
    name: str
    color: Optional[str] = None

class TagCreate(TagBase):
    pass

class Tag(TagBase):
    id: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class LogBase(BaseModel):
    content: str

class LogCreate(LogBase):
    id: UUID4  # Client must provide the ID
    tags: List[str] = []  # List of tag names

class LogUpdate(LogBase):
    pass

class LogResponse(LogBase):
    id: UUID4
    weaviate_id: Optional[str]  # Include weaviate_id in response
    created_at: datetime
    updated_at: datetime
    word_count: Optional[int]
    processing_status: Optional[str]
    tags: List[Tag]

    class Config:
        from_attributes = True 