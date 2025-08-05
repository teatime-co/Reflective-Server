from pydantic import BaseModel, UUID4
from typing import Optional, Dict
from datetime import datetime

class SessionCreate(BaseModel):
    session_type: str = "freeform"

class SessionResponse(BaseModel):
    id: UUID4
    user_id: UUID4
    started_at: datetime
    ended_at: Optional[datetime] = None
    session_type: str
    interruption_count: int
    focus_score: Optional[float] = None

    class Config:
        from_attributes = True 