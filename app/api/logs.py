from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import re
import time
from pydantic import UUID4
import traceback
import sys

from app.database import get_db
from app.models.models import Log, Tag, Query as QueryModel, QueryResult as QueryResultModel, log_theme_association
from app.services.weaviate_rag_service import WeaviateRAGService
from app.schemas.log import LogCreate, LogResponse, LogUpdate, Tag as TagSchema
from app.schemas.query import SearchResult, QueryWithScore
from app.utils.uuid_utils import format_uuid_from_weaviate, format_uuid_for_weaviate
from app.api.auth import get_current_user
from app.schemas.user import UserResponse
from app.api.tags import get_or_create_tag
from app.schemas.query import SearchRequest

router = APIRouter()
rag_service = WeaviateRAGService() # pass False to run cloud service instead

def extract_tags(content: str) -> List[str]:
    """Extract hashtags from content, ignoring escaped hashtags"""
    # Replace escaped hashtags temporarily
    escaped_content = content.replace("\\#", "ESCAPED_HASHTAG_PLACEHOLDER")
    # Extract hashtags
    tags = re.findall(r'#([\w\d_-]+)', escaped_content)
    return list(set(tags))

@router.post("/logs/", response_model=LogResponse, status_code=status.HTTP_201_CREATED)
async def create_log(
    log_data: LogCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new log entry"""
    print(f"[DEBUG] Received create_log request with data: {log_data}")
    
    # Add log to Weaviate
    weaviate_id = rag_service.add_log(log_data.content, log_data.tags)
    print(f"[DEBUG] Weaviate ID: {weaviate_id}")
    if not weaviate_id:
        print("[ERROR] Failed to create log in vector database")
        raise HTTPException(status_code=500, detail="Failed to create log in vector database")
    
    # Create log in SQL database with client-provided ID and user_id
    new_log = Log(
        id=log_data.id,
        user_id=current_user.id,  # Add user_id from authenticated user
        weaviate_id=weaviate_id,
        content=log_data.content,
        word_count=len(log_data.content.split()),
        processing_status="processed",
        mood_score=getattr(log_data, 'mood_score', None),
        completion_status=getattr(log_data, 'completion_status', 'draft'),
        target_word_count=getattr(log_data, 'target_word_count', 750),
        writing_duration=getattr(log_data, 'writing_duration', None),
        session_id=getattr(log_data, 'session_id', None),
        prompt_id=getattr(log_data, 'prompt_id', None)
    )
    
    try:
        db.add(new_log)
        
        # Process tags from request
        for tag_name in log_data.tags:
            try:
                tag = await get_or_create_tag(tag_name, current_user, db)
                new_log.tags.append(tag)
            except Exception as tag_error:
                print(f"[ERROR] Failed to create/get tag {tag_name}: {str(tag_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to process tag {tag_name}: {str(tag_error)}")
        
        db.commit()
        db.refresh(new_log)
        return new_log
    except Exception as e:
        # If SQL insertion fails, cleanup Weaviate entry
        rag_service.delete_log(weaviate_id)
        db.rollback()
        print(f"[ERROR] Failed to create log: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/logs/", response_model=List[LogResponse], status_code=status.HTTP_200_OK)
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    tag: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get logs with optional filtering"""
    query = db.query(Log).filter(Log.user_id == current_user.id)  # Filter by user_id
    
    if tag:
        print(f"Searching for tag: {tag}")
        # Get tag from database
        db_tag = Tag.get_or_create(db, tag)
        
        # Get logs that have this tag
        logs = query.filter(Log.tags.any(Tag.id == db_tag.id)).all()
        return logs
    
    # Regular pagination without search
    return query.order_by(Log.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/logs/{log_id}", response_model=LogResponse, status_code=status.HTTP_200_OK)
async def get_log(
    log_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific log by ID"""
    log = db.query(Log).filter(
        Log.id == log_id,
        Log.user_id == current_user.id  # Ensure user owns the log
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log

@router.put("/logs/{log_id}", response_model=LogResponse, status_code=status.HTTP_200_OK)
async def update_log(
    log_id: str,
    log_data: LogUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a log entry"""
    log = db.query(Log).filter(
        Log.id == log_id,
        Log.user_id == current_user.id  # Ensure user owns the log
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    # Determine which tags to use: explicit tags from client, or extracted from content
    tag_names = log_data.tags if log_data.tags else extract_tags(log_data.content)
    
    # Update in Weaviate if content changed or if we have a valid weaviate_id
    weaviate_updated = False
    if log.weaviate_id and log_data.content != log.content:
        try:
            # Format the weaviate_id properly (remove hyphens)
            formatted_weaviate_id = format_uuid_for_weaviate(log.weaviate_id)
            weaviate_updated = rag_service.update_log(formatted_weaviate_id, log_data.content, tag_names)
            
            if not weaviate_updated:
                print(f"[WARN] Failed to update Weaviate entry {log.weaviate_id}, but continuing with SQL update")
        except Exception as e:
            print(f"[WARN] Weaviate update failed for log {log_id}: {e}, but continuing with SQL update")
    
    # Update all fields in SQL database
    log.content = log_data.content
    log.word_count = len(log_data.content.split())
    log.processing_status = "processed"
    log.updated_at = datetime.utcnow()
    
    # Update LogBase fields from LogUpdate
    if hasattr(log_data, 'mood_score') and log_data.mood_score is not None:
        log.mood_score = log_data.mood_score
    if hasattr(log_data, 'completion_status') and log_data.completion_status is not None:
        log.completion_status = log_data.completion_status
    if hasattr(log_data, 'target_word_count') and log_data.target_word_count is not None:
        log.target_word_count = log_data.target_word_count
    if hasattr(log_data, 'writing_duration') and log_data.writing_duration is not None:
        log.writing_duration = log_data.writing_duration
    if hasattr(log_data, 'session_id') and log_data.session_id is not None:
        log.session_id = log_data.session_id
    if hasattr(log_data, 'prompt_id') and log_data.prompt_id is not None:
        log.prompt_id = log_data.prompt_id
    
    # Update tags
    current_tags = {tag.name: tag for tag in log.tags}
    
    # Remove tags that are no longer present
    log.tags = [tag for tag in log.tags if tag.name in tag_names]
    
    # Add new tags
    for tag_name in tag_names:
        if tag_name not in current_tags:
            try:
                tag = await get_or_create_tag(tag_name, current_user, db)
                log.tags.append(tag)
            except Exception as tag_error:
                print(f"[ERROR] Failed to create/get tag {tag_name}: {str(tag_error)}")
                raise HTTPException(status_code=500, detail=f"Failed to process tag {tag_name}: {str(tag_error)}")
    
    try:
        db.commit()
        db.refresh(log)
    except Exception as e:
        print(f"[ERROR] Failed to update log: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    return log

@router.delete("/logs/{log_id}", status_code=status.HTTP_200_OK)
async def delete_log(
    log_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a log entry"""
    log = db.query(Log).filter(
        Log.id == log_id,
        Log.user_id == current_user.id  # Ensure user owns the log
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    # Delete from Weaviate
    if not rag_service.delete_log(log.weaviate_id):
        raise HTTPException(status_code=500, detail="Failed to delete log from vector database")
    
    # Delete from SQL database
    db.delete(log)
    db.commit()
    
    return {"message": "Log deleted successfully"}

@router.post("/logs/search", response_model=List[SearchResult], status_code=status.HTTP_200_OK)
async def semantic_search(
    request: SearchRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Perform semantic search on logs and return full log details with search metadata"""
    start_time = time.time()
    
    try:
        # Extract values from request body
        query = request.query
        top_k = request.top_k
        
        # Create new query record with user_id (always create new, no duplicate checking)
        print(f"[DEBUG] Creating new query record for: {query}")
        query_record = QueryModel(
            user_id=current_user.id,
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
        
        # Get the corresponding logs from SQL database (filtered by user_id)
        weaviate_ids = [result["id"] for result in search_results]
        print(f"[DEBUG] Looking up logs with Weaviate IDs: {weaviate_ids}")
        logs = db.query(Log).options(
            joinedload(Log.tags),
            joinedload(Log.themes),
            joinedload(Log.linguistic_metrics),
            joinedload(Log.revisions)
        ).filter(
            Log.weaviate_id.in_(weaviate_ids),
            Log.user_id == current_user.id  # Filter by user_id
        ).all()
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
                
                # Add themes from relationship with association data
                theme_data = []
                if log.themes:
                    # Get theme association data (confidence_score, detected_at)
                    theme_associations = db.query(log_theme_association).filter(
                        log_theme_association.c.log_id == log.id
                    ).all()
                    
                    # Create a mapping of theme_id to association data
                    association_map = {
                        assoc.theme_id: {
                            "confidence_score": assoc.confidence_score,
                            "detected_at": assoc.detected_at
                        } for assoc in theme_associations
                    }
                    
                    # Build theme data with association info
                    for theme in log.themes:
                        theme_info = {
                            "id": theme.id,
                            "name": theme.name,
                            "description": theme.description,
                            "confidence_threshold": theme.confidence_threshold,
                            "created_at": theme.created_at,
                            "updated_at": theme.updated_at  # Add the missing updated_at field
                        }
                        
                        # Add association data if available
                        if theme.id in association_map:
                            theme_info.update(association_map[theme.id])
                        else:
                            # Fallback values if association data is missing
                            theme_info["confidence_score"] = 0.0
                            theme_info["detected_at"] = theme.created_at
                        
                        theme_data.append(theme_info)
                
                log_dict['themes'] = theme_data
                
                # Add linguistic metrics from relationship
                metrics = log.linguistic_metrics
                log_dict['linguistic_metrics'] = {
                    "id": metrics.id,
                    "log_id": metrics.log_id,
                    "vocabulary_diversity_score": metrics.vocabulary_diversity_score,
                    "sentiment_score": metrics.sentiment_score,
                    "complexity_score": metrics.complexity_score,
                    "readability_level": metrics.readability_level,
                    "emotion_scores": metrics.emotion_scores,
                    "writing_style_metrics": metrics.writing_style_metrics,
                    "processed_at": metrics.processed_at
                } if metrics else None
                
                # Add revisions from relationship
                log_dict['revisions'] = [
                    {
                        "id": rev.id,
                        "log_id": rev.log_id,
                        "revision_number": rev.revision_number,
                        "content_delta": rev.content_delta,
                        "revision_type": rev.revision_type,
                        "created_at": rev.created_at
                    } for rev in log.revisions
                ] if log.revisions else []
                
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
        
        # Always update the execution metadata for this search
        query_record.execution_time = execution_time
        query_record.result_count = result_count
        
        # Commit SQL changes first (whether new or updated)
        db.commit()
        
        # Store query in Weaviate with the committed ID
        # The add_query method will handle deduplication internally
        print(f"[DEBUG] Storing/checking query in Weaviate with ID: {query_record.id}")
        weaviate_id = rag_service.add_query(
            query_text=query,
            sql_id=str(query_record.id),
            result_count=result_count,
            execution_time=execution_time
        )
        
        if weaviate_id:
            print(f"[DEBUG] Query stored in Weaviate with ID: {weaviate_id}")
        else:
            print(f"[WARN] Failed to store query in Weaviate")
        
        return combined_results
        
    except Exception as e:
        print(f"[ERROR] Semantic search failed:")
        print(f"Query: {query}")
        print(f"Error: {str(e)}")
        print("Traceback:")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}\n{traceback.format_exc()}")

@router.get("/logs/search/similar", response_model=List[QueryWithScore], status_code=status.HTTP_200_OK)
async def get_similar_queries(
    query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    min_certainty: float = Query(default=0.7, ge=0.0, le=1.0),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get similar previous queries"""
    try:
        similar_queries = rag_service.get_similar_queries(query, limit, min_certainty)
        
        # Convert to response format and filter by user_id
        return [
            QueryWithScore(
                id=q["sql_id"],
                query_text=q["query_text"],
                created_at=q["created_at"],
                result_count=q["result_count"],
                relevance_score=q["relevance_score"]
            ) for q in similar_queries
            if db.query(QueryModel).filter(
                QueryModel.id == q["sql_id"],
                QueryModel.user_id == current_user.id
            ).first()
        ]
    except ValueError as e:
        print(f"[ERROR] Failed to convert UUID: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Failed to get similar queries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get similar queries: {str(e)}")

@router.get("/logs/search/suggest", response_model=List[QueryWithScore], status_code=status.HTTP_200_OK)
async def get_query_suggestions(
    partial_query: str = Query(..., min_length=1),
    limit: int = Query(default=5, ge=1, le=20),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get query suggestions based on partial input"""
    try:
        suggestions = rag_service.get_query_suggestions(partial_query, limit)
        
        # Convert to response format and filter by user_id
        return [
            QueryWithScore(
                id=q["sql_id"],
                query_text=q["query_text"],
                created_at=q["created_at"],
                result_count=q["result_count"]
            ) for q in suggestions
            if db.query(QueryModel).filter(
                QueryModel.id == q["sql_id"],
                QueryModel.user_id == current_user.id
            ).first()
        ]
    except ValueError as e:
        print(f"[ERROR] Failed to convert UUID: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid UUID format: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Failed to get query suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get query suggestions: {str(e)}") 