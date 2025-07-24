from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List

class QueryBase(BaseModel):
    query_text: str

class QueryCreate(QueryBase):
    pass

class QueryResultBase(BaseModel):
    relevance_score: float
    snippet_text: str
    snippet_start_index: int
    snippet_end_index: int
    context_before: Optional[str]
    context_after: Optional[str]
    rank: int

class QueryResult(QueryResultBase):
    id: UUID4
    query_id: UUID4
    log_id: UUID4

    class Config:
        from_attributes = True

class Query(QueryBase):
    id: UUID4
    created_at: datetime
    execution_time: Optional[float]
    result_count: Optional[int]
    results: List[QueryResult]

    class Config:
        from_attributes = True

class QueryResponse(QueryResult):
    log_content: str  # Include the full log content in the response

    class Config:
        from_attributes = True 