from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import Tag
from app.schemas.log import Tag as TagSchema

router = APIRouter()

@router.get("/tags", response_model=List[TagSchema])
async def get_tags(db: Session = Depends(get_db)):
    """Get all tags"""
    tags = db.query(Tag).order_by(Tag.name).all()
    return tags

@router.delete("/tags/cleanup")
async def cleanup_stale_tags(
    days: int = Query(default=30, ge=1, description="Number of days of inactivity to consider a tag stale"),
    db: Session = Depends(get_db)
):
    """
    Clean up stale tags that haven't been used in the specified number of days and have no associated logs.
    Returns the number of tags deleted.
    """
    # Calculate the cutoff date
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Find stale tags that have no associated logs
    stale_tags = db.query(Tag).filter(
        Tag.last_used_at < cutoff_date,
        ~Tag.logs.any()  # No associated logs
    ).all()
    
    # Delete the stale tags
    deleted_count = 0
    for tag in stale_tags:
        db.delete(tag)
        deleted_count += 1
    
    db.commit()
    
    return {"message": f"Successfully deleted {deleted_count} stale tags", "deleted_count": deleted_count} 