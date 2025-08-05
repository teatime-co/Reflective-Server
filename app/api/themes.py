from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.services.theme_service import theme_service
from app.api.auth import get_current_user
from app.models.models import User, Theme, Log
from app.schemas.themes import (
    ThemeCreate, 
    ThemeUpdate, 
    ThemeResponse, 
    ThemeWithLogsResponse,
    ThemeMatch,
    ThemeSuggestion
)
from datetime import datetime, timedelta
from starlette.responses import JSONResponse

router = APIRouter(
    prefix="/themes",
    tags=["themes"],
    responses={404: {"description": "Not found"}}
)

@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
def create_theme(
    theme_data: ThemeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new theme for the current user.
    If theme already exists, update its description if provided.
    """
    # Check if theme already exists before creating
    existing_theme = db.query(Theme).filter_by(
        user_id=str(current_user.id),
        name=theme_data.name
    ).first()
    
    theme = theme_service.create_theme(
        db, 
        str(current_user.id), 
        theme_data.name, 
        theme_data.description
    )
    
    # If theme already existed, return 200 instead of 201
    if existing_theme:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Theme already exists",
                "theme": {
                    "id": str(theme.id),
                    "user_id": str(theme.user_id),
                    "name": theme.name,
                    "description": theme.description,
                    "created_at": theme.created_at.isoformat()
                }
            }
        )
    
    return theme

@router.get("", response_model=List[ThemeResponse])
def get_themes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all themes for the current user"""
    return theme_service.get_user_themes(db, str(current_user.id))

@router.post("/detect/{log_id}", response_model=List[ThemeMatch])
def detect_themes(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Detect themes in a log entry"""
    print("\n=== Debug: detect_themes endpoint ===")
    log = db.query(Log).filter_by(id=log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    if str(log.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this log")
    
    print(f"Processing log: {log.content}")
    matches = theme_service.process_log(db, log)
    print(f"Theme matches: {matches}")
    return matches

@router.post("/suggest", response_model=ThemeSuggestion)
def suggest_themes(
    text: str = Query(..., description="Text content to generate theme suggestions for"),
    max_suggestions: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get theme suggestions for text content"""
    suggestions = theme_service.get_theme_suggestions(db, text, str(current_user.id), max_suggestions)
    return ThemeSuggestion(suggested_themes=suggestions)

@router.get("/{theme_id}", response_model=ThemeResponse)
def get_theme(
    theme_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific theme"""
    theme = theme_service.get_theme(db, theme_id, str(current_user.id))
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme 