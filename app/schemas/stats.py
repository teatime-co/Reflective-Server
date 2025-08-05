from pydantic import BaseModel

class UserWritingStats(BaseModel):
    total_logs: int
    recent_logs: int
    total_words: int
    avg_words_per_entry: float
    writing_streak: int
    days_analyzed: int

    class Config:
        from_attributes = True 