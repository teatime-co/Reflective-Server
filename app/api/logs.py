from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import re
import traceback

from app.database import get_db
from app.models.models import Log, Tag
from app.services.weaviate_rag_service import WeaviateRAGService
from app.schemas.log import LogCreate, LogResponse, LogUpdate
from app.utils.uuid_utils import format_uuid_for_weaviate
from app.api.auth import get_current_user
from app.schemas.user import UserResponse
from app.api.tags import get_or_create_tag

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
        # Get tag from database for this user
        db_tag = Tag.get_or_create(db, tag, current_user.id)

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