from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uuid

from app.database import get_db
from app.models.models import Tag, Log
from app.schemas.tags import TagResponse, TagCreate, TagUpdate
from app.api.auth import get_current_user
from app.schemas.user import UserResponse

router = APIRouter()

async def get_or_create_tag(
    name: str,
    current_user: UserResponse,
    db: Session,
    color: Optional[str] = None
) -> Tag:
    """Utility function to get or create a tag"""
    # First check for existing tag by name only
    existing_tag = db.query(Tag).filter(Tag.name == name).first()
    
    if existing_tag:
        # Check if this user has any logs with this tag
        user_has_tag = db.query(Log).join(Log.tags).filter(
            Log.user_id == current_user.id,
            Tag.id == existing_tag.id
        ).first() is not None
        
        # Return existing tag regardless of user association
        # This allows sharing tags between users
        return existing_tag
    
    # Create new tag if it doesn't exist
    new_tag = Tag(
        id=uuid.uuid4(),
        name=name,
        color=color or Tag.generate_random_color(),
        created_at=datetime.utcnow(),
        last_used_at=datetime.utcnow()
    )
    
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    return new_tag

@router.get("/tags", response_model=List[TagResponse], status_code=status.HTTP_200_OK)
async def get_tags(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tags used by the current user"""
    # Get tags that are associated with the user's logs
    tags = (
        db.query(Tag)
        .join(Tag.logs)
        .filter(Log.user_id == current_user.id)
        .distinct()
        .order_by(Tag.name)
        .all()
    )
    return tags

@router.post("/tags", response_model=TagResponse)
async def create_tag(
    tag: TagCreate,
    response: Response,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new tag or return existing one if name already exists"""
    # First check for existing tag by name only
    existing_tag = db.query(Tag).filter(Tag.name == tag.name).first()
    
    if existing_tag:
        # Check if this user has any logs with this tag
        user_has_tag = db.query(Log).join(Log.tags).filter(
            Log.user_id == current_user.id,
            Tag.id == existing_tag.id
        ).first() is not None
        
        if user_has_tag:
            response.status_code = status.HTTP_200_OK
            return existing_tag
    
    # Create new tag if no existing tag or user doesn't have access to it
    db_tag = Tag(
        id=uuid.uuid4(),
        name=tag.name,
        color=tag.color or Tag.generate_random_color(),
        created_at=datetime.utcnow(),
        last_used_at=datetime.utcnow()
    )
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    
    response.status_code = status.HTTP_201_CREATED
    return db_tag

@router.delete("/tags/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_stale_tags(
    days: int = Query(default=30, ge=1, description="Number of days of inactivity to consider a tag stale"),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Clean up stale tags that haven't been used in the specified number of days and have no associated logs
    from the current user. Returns the number of tags deleted.
    """
    # Calculate the cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Find stale tags that have no associated logs from this user
    stale_tags = db.query(Tag).filter(
        Tag.last_used_at < cutoff_date,
        ~Tag.logs.any(Log.user_id == current_user.id)  # No associated logs from this user
    ).all()
    
    # Delete the stale tags
    deleted_count = 0
    for tag in stale_tags:
        # Only delete if no other users are using this tag
        if not db.query(Log).join(Log.tags).filter(
            Tag.id == tag.id,
            Log.user_id != current_user.id
        ).first():
            db.delete(tag)
            deleted_count += 1
    
    db.commit()
    
    return {"message": f"Successfully deleted {deleted_count} stale tags", "deleted_count": deleted_count} 