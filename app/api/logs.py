from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import re

from app.database import get_db
from app.models.models import Log, Tag
from app.services.weaviate_rag_service import WeaviateRAGService
from app.schemas.log import LogCreate, LogResponse, LogUpdate, Tag as TagSchema
from app.schemas.query import QueryResponse

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
    
    # Extract tags from content
    tag_names = extract_tags(log_data.content)
    print(f"[DEBUG] Extracted tags: {tag_names}")
    
    # Add log to Weaviate
    weaviate_id = rag_service.add_log(log_data.content, tag_names)
    print(f"[DEBUG] Weaviate ID: {weaviate_id}")
    if not weaviate_id:
        print("[ERROR] Failed to create log in vector database")
        raise HTTPException(status_code=500, detail="Failed to create log in vector database")
    
    # Create log in SQL database
    new_log = Log(
        id=weaviate_id,
        content=log_data.content,
        word_count=len(log_data.content.split()),
        processing_status="processed"
    )
    db.add(new_log)
    
    # Process tags
    for tag_name in tag_names:
        tag = Tag.get_or_create(db, tag_name)
        new_log.tags.append(tag)
    
    db.commit()
    db.refresh(new_log)
    return new_log

@router.get("/logs/", response_model=List[LogResponse])
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get logs with optional filtering"""
    if tag:
        # Use Weaviate for tag-based search
        weaviate_results = rag_service.get_logs_by_tag(tag, limit)
        log_ids = [result["id"] for result in weaviate_results]
        return db.query(Log).filter(Log.id.in_(log_ids)).all()
    
    if search:
        # Use Weaviate for semantic search
        weaviate_results = rag_service.semantic_search(search, limit)
        log_ids = [result["id"] for result in weaviate_results]
        return db.query(Log).filter(Log.id.in_(log_ids)).all()
    
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
        if not rag_service.update_log(log_id, log_data.content, new_tag_names):
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
    if not rag_service.delete_log(log_id):
        raise HTTPException(status_code=500, detail="Failed to delete log from vector database")
    
    # Delete from SQL database
    db.delete(log)
    db.commit()
    
    return {"message": "Log deleted successfully"}

@router.post("/search", response_model=List[QueryResponse])
async def semantic_search(
    query: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Perform semantic search on logs"""
    results = rag_service.semantic_search(query, top_k)
    return results 