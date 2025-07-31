from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import re
import time
from pydantic import UUID4
import traceback
import sys

from app.database import get_db
from app.models.models import Log, Tag, Query as QueryModel, QueryResult as QueryResultModel
from app.services.weaviate_rag_service import WeaviateRAGService
from app.schemas.log import LogCreate, LogResponse, LogUpdate, Tag as TagSchema
from app.schemas.query import SearchResult, QueryWithScore
from app.utils.uuid_helpers import format_uuid_from_weaviate

router = APIRouter()
rag_service = WeaviateRAGService() # pass False to run cloud service instead

def extract_tags(content: str) -> List[str]:
    """Extract hashtags from content, ignoring escaped hashtags"""
    # Replace escaped hashtags temporarily
    escaped_content = content.replace("\\#", "ESCAPED_HASHTAG_PLACEHOLDER")
    # Extract hashtags
    tags = re.findall(r'#([\w\d_-]+)', escaped_content)
    return list(set(tags))

@router.get("/tags", response_model=List[TagSchema])
async def get_tags(db: Session = Depends(get_db)):
    """Get all tags"""
    tags = db.query(Tag).order_by(Tag.name).all()
    return tags

@router.post("/tags", response_model=TagSchema)
async def create_tag(tag: TagSchema, db: Session = Depends(get_db)):
    """Create a new tag"""
    existing_tag = db.query(Tag).filter(Tag.name == tag.name).first()
    if existing_tag:
        return existing_tag
        
    new_tag = Tag(
        id=tag.id,
        name=tag.name,
        color=tag.color,
        created_at=tag.created_at
    )
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag

@router.post("/logs/", response_model=LogResponse)
async def create_log(log_data: LogCreate, db: Session = Depends(get_db)):
    """Create a new log entry"""
    print(f"[DEBUG] Received create_log request with data: {log_data}")
    
    # Add log to Weaviate
    weaviate_id = rag_service.add_log(log_data.content, log_data.tags)
    print(f"[DEBUG] Weaviate ID: {weaviate_id}")
    if not weaviate_id:
        print("[ERROR] Failed to create log in vector database")
        raise HTTPException(status_code=500, detail="Failed to create log in vector database")
    
    # Create log in SQL database with client-provided ID
    new_log = Log(
        id=log_data.id,
        weaviate_id=weaviate_id,
        content=log_data.content,
        word_count=len(log_data.content.split()),
        processing_status="processed"
    )
    
    try:
        db.add(new_log)
        
        # Process tags from request
        for tag_name in log_data.tags:
            tag = Tag.get_or_create(db, tag_name)
            new_log.tags.append(tag)
        
        db.commit()
        db.refresh(new_log)
        return new_log
    except Exception as e:
        # If SQL insertion fails, cleanup Weaviate entry
        rag_service.delete_log(weaviate_id)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/", response_model=List[LogResponse])
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get logs with optional filtering"""
    if tag:
        # Use Weaviate for tag-based search
        weaviate_results = rag_service.get_logs_by_tag(tag, limit)
        weaviate_ids = [result["id"] for result in weaviate_results]
        return db.query(Log).filter(Log.weaviate_id.in_(weaviate_ids)).all()
    
    # Regular pagination without search
    return db.query(Log).order_by(Log.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/logs/{log_id}", response_model=LogResponse)
async def get_log(log_id: str, db: Session = Depends(get_db)):
    """Get a specific log by ID"""
    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log

@router.put("/logs/{log_id}", response_model=LogResponse)
async def update_log(log_id: str, log_data: LogUpdate, db: Session = Depends(get_db)):
    """Update a log entry"""
    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    # Update content if changed
    if log_data.content != log.content:
        # Extract new tags
        new_tag_names = extract_tags(log_data.content)
        
        # Update in Weaviate
        if not rag_service.update_log(log.weaviate_id, log_data.content, new_tag_names):
            raise HTTPException(status_code=500, detail="Failed to update log in vector database")
        
        # Update in SQL database
        log.content = log_data.content
        log.word_count = len(log_data.content.split())
        log.processing_status = "processed"
        log.updated_at = datetime.utcnow()
        
        # Update tags
        current_tags = {tag.name: tag for tag in log.tags}
        
        # Remove tags that are no longer present
        log.tags = [tag for tag in log.tags if tag.name in new_tag_names]
        
        # Add new tags
        for tag_name in new_tag_names:
            if tag_name not in current_tags:
                tag = Tag.get_or_create(db, tag_name)
                log.tags.append(tag)
        
        db.commit()
        db.refresh(log)
    
    return log

@router.delete("/logs/{log_id}")
async def delete_log(log_id: str, db: Session = Depends(get_db)):
    """Delete a log entry"""
    log = db.query(Log).filter(Log.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    # Delete from Weaviate
    if not rag_service.delete_log(log.weaviate_id):
        raise HTTPException(status_code=500, detail="Failed to delete log from vector database")
    
    # Delete from SQL database
    db.delete(log)
    db.commit()
    
    return {"message": "Log deleted successfully"}

@router.post("/search", response_model=List[SearchResult])
async def semantic_search(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Perform semantic search on logs and return full log details with search metadata"""
    start_time = time.time()
    
    try:
        # Create query record
        print(f"[DEBUG] Creating query record for: {query}")
        query_record = QueryModel(
            query_text=query,
            created_at=datetime.utcnow()
        )
        db.add(query_record)
        
        # Get search results from Weaviate
        print(f"[DEBUG] Performing semantic search with top_k={top_k}")
        search_results = rag_service.semantic_search(query, top_k)
        print(f"[DEBUG] Got {len(search_results) if search_results else 0} results from Weaviate")
        if search_results:
            print(f"[DEBUG] First result structure: {search_results[0]}")
        
        # Get the corresponding logs from SQL database
        weaviate_ids = [result["id"] for result in search_results]
        print(f"[DEBUG] Looking up logs with Weaviate IDs: {weaviate_ids}")
        logs = db.query(Log).filter(Log.weaviate_id.in_(weaviate_ids)).all()
        print(f"[DEBUG] Found {len(logs)} matching logs in SQL database")
        log_map = {log.weaviate_id: log for log in logs}
        
        # Process search results
        combined_results = []
        for rank, result in enumerate(search_results, 1):  # Start rank at 1
            log = log_map.get(result["id"])
            if not log:
                print(f"[WARN] No SQL log found for Weaviate ID: {result['id']}")
                continue
                
            # Extract search metadata
            print(f"[DEBUG] Processing result {rank} with Weaviate ID: {result['id']}")
            search_metadata = {
                "relevance_score": result.get("relevance_score", 0.0),
                "snippet_text": result.get("snippet_text", ""),
                "snippet_start_index": result.get("snippet_start_index", 0),
                "snippet_end_index": result.get("snippet_end_index", 0),
                "context_before": result.get("context_before"),
                "context_after": result.get("context_after"),
                "rank": rank
            }
            
            try:
                # Store query result
                db.add(QueryResultModel(
                    query=query_record,
                    log=log,
                    **search_metadata
                ))
                
                # Create response object
                print(f"[DEBUG] Creating SearchResult for log ID: {log.id}")
                log_dict = log.__dict__.copy()
                
                # Remove SQLAlchemy state
                log_dict.pop('_sa_instance_state', None)
                
                # Add tags properly
                log_dict['tags'] = [
                    {
                        "id": tag.id,
                        "name": tag.name,
                        "color": tag.color,
                        "created_at": tag.created_at
                    } for tag in log.tags
                ]
                
                response_obj = SearchResult(
                    **log_dict,
                    **search_metadata
                )
                combined_results.append(response_obj)
            except Exception as inner_e:
                print(f"[ERROR] Failed to process result {rank}:")
                print(f"Log data: {log.__dict__}")
                print(f"Search metadata: {search_metadata}")
                print(f"Error: {str(inner_e)}")
                traceback.print_exc()
                continue
        
        # Update query metadata and store in both SQL and Weaviate
        execution_time = time.time() - start_time
        result_count = len(combined_results)
        
        query_record.execution_time = execution_time
        query_record.result_count = result_count
        
        # Commit SQL changes first
        db.commit()
        
        # Now store query in Weaviate with the committed ID
        print(f"[DEBUG] Storing query in Weaviate with ID: {query_record.id}")
        rag_service.add_query(
            query_text=query,
            sql_id=str(query_record.id),
            result_count=result_count,
            execution_time=execution_time
        )
        
        return combined_results
        
    except Exception as e:
        print(f"[ERROR] Semantic search failed:")
        print(f"Query: {query}")
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}\n{traceback.format_exc()}")

@router.get("/search/similar", response_model=List[QueryWithScore])
async def get_similar_queries(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    min_certainty: float = Query(default=0.7, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """Get similar previous queries"""
    try:
        similar_queries = rag_service.get_similar_queries(query, limit, min_certainty)
        
        # Convert to response format
        return [
            QueryWithScore(
                id=q["sql_id"],  # Just use the string UUID directly
                query_text=q["query_text"],
                created_at=q["created_at"],
                result_count=q["result_count"],
                relevance_score=q["relevance_score"]
            ) for q in similar_queries
        ]
    except ValueError as e:
        print(f"[ERROR] Failed to convert UUID: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Failed to get similar queries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar queries: {str(e)}")

@router.get("/search/suggest", response_model=List[QueryWithScore])
async def get_query_suggestions(
    partial_query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get query suggestions based on partial input"""
    try:
        suggestions = rag_service.get_query_suggestions(partial_query, limit)
        
        # Convert to response format
        return [
            QueryWithScore(
                id=q["sql_id"],  # Just use the string UUID directly
                query_text=q["query_text"],
                created_at=q["created_at"],
                result_count=q["result_count"]
            ) for q in suggestions
        ]
    except ValueError as e:
        print(f"[ERROR] Failed to convert UUID: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Failed to get query suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get query suggestions: {str(e)}") 