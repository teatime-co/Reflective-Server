from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

class TagBase(BaseModel):
    name: str
    color: Optional[str] = None

class TagCreate(TagBase):
    pass

class TagUpdate(TagBase):
    name: Optional[str] = None
    color: Optional[str] = None

class TagResponse(TagBase):
    id: UUID4
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True 