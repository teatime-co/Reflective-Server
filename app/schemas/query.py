from pydantic import BaseModel, UUID4, Field
from datetime import datetime
from typing import Optional, List
from .log import LogResponse

class SearchRequest(BaseModel):
    """Request schema for semantic search"""
    query: str = Field(..., min_length=1, description="Search query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of results to return")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "feeling grateful today",
                "top_k": 5
            }
        }

class QueryBase(BaseModel):
    """Base schema for queries"""
    query_text: str
    created_at: datetime
    execution_time: Optional[float] = None
    result_count: Optional[int] = None

    class Config:
        from_attributes = True

class SearchMetadata(BaseModel):
    """Search-specific metadata"""
    relevance_score: float
    snippet_text: str
    snippet_start_index: int
    snippet_end_index: int
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    rank: int

    class Config:
        from_attributes = True

class SearchResult(LogResponse, SearchMetadata):
    """Complete search result combining log data with search metadata"""
    class Config:
        from_attributes = True

class QueryResult(SearchMetadata):
    """Database model for search results"""
    id: UUID4
    query_id: UUID4
    log_id: UUID4

    class Config:
        from_attributes = True

class Query(QueryBase):
    """Complete query record"""
    id: UUID4
    results: List[QueryResult]

    class Config:
        from_attributes = True

class QueryWithScore(QueryBase):
    """Query with similarity score for suggestions and similar queries"""
    id: str  # Store UUID as string to avoid conversion issues
    relevance_score: Optional[float] = None  # Used for similar queries

    class Config:
        from_attributes = True 