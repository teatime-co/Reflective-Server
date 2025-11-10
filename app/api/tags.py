from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import uuid

from app.database import get_db
from app.models.models import Tag
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
    """Utility function to get or create a tag for the current user"""
    # Check for existing tag by name and user_id
    existing_tag = db.query(Tag).filter(
        Tag.name == name,
        Tag.user_id == current_user.id
    ).first()

    if existing_tag:
        # Update last_used_at
        existing_tag.last_used_at = datetime.utcnow()
        if color and existing_tag.color != color:
            existing_tag.color = color
        return existing_tag

    # Create new tag for this user
    new_tag = Tag(
        id=uuid.uuid4(),
        user_id=current_user.id,
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
    """Get all tags created by the current user"""
    tags = (
        db.query(Tag)
        .filter(Tag.user_id == current_user.id)
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
    """Create a new tag or return existing one if name already exists for this user"""
    # Check for existing tag by name and user_id
    existing_tag = db.query(Tag).filter(
        Tag.name == tag.name,
        Tag.user_id == current_user.id
    ).first()

    if existing_tag:
        response.status_code = status.HTTP_200_OK
        return existing_tag

    # Create new tag for this user
    db_tag = Tag(
        id=uuid.uuid4(),
        user_id=current_user.id,
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
    Clean up stale tags that haven't been used in the specified number of days.
    Returns the number of tags deleted.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    stale_tags = db.query(Tag).filter(
        Tag.user_id == current_user.id,
        Tag.last_used_at < cutoff_date
    ).all()

    deleted_count = len(stale_tags)
    for tag in stale_tags:
        db.delete(tag)

    db.commit()

    return {"message": f"Successfully deleted {deleted_count} stale tags", "deleted_count": deleted_count} 