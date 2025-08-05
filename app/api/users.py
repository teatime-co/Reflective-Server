from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User, Log, WritingSession
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.schemas.stats import UserWritingStats
from app.api.auth import get_current_user
from app.services.auth_service import update_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current user's profile"""
    return current_user

@router.put("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Get the actual user model instance
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user data
    update_data = user_update.dict(exclude_unset=True)
    updated_user = update_user(db, user, update_data)
    return UserResponse.model_validate(updated_user)

@router.get("/me/stats", response_model=UserWritingStats, status_code=status.HTTP_200_OK)
async def get_user_stats(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30
):
    """Get user's writing statistics"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Get basic stats
    total_logs = db.query(Log).filter(
        Log.user_id == current_user.id
    ).count()
    
    recent_logs = db.query(Log).filter(
        Log.user_id == current_user.id,
        Log.created_at >= cutoff_date
    ).all()
    
    total_words = sum(log.word_count or 0 for log in recent_logs)
    avg_words_per_entry = total_words / len(recent_logs) if recent_logs else 0
    
    # Get writing streak
    writing_sessions = db.query(WritingSession).filter(
        WritingSession.user_id == current_user.id,
        WritingSession.started_at >= cutoff_date
    ).order_by(WritingSession.started_at.desc()).all()
    
    streak = 0
    if writing_sessions:
        current_date = datetime.utcnow().date()
        last_session_date = writing_sessions[0].started_at.date()
        
        # If no session today, start from yesterday
        if last_session_date < current_date:
            current_date = current_date - timedelta(days=1)
        
        # Count consecutive days
        session_dates = {session.started_at.date() for session in writing_sessions}
        while current_date in session_dates:
            streak += 1
            current_date = current_date - timedelta(days=1)
    
    return UserWritingStats(
        total_logs=total_logs,
        recent_logs=len(recent_logs),
        total_words=total_words,
        avg_words_per_entry=round(avg_words_per_entry, 2),
        writing_streak=streak,
        days_analyzed=days
    )

@router.get("/me/preferences", response_model=UserPreferencesResponse, status_code=status.HTTP_200_OK)
async def get_user_preferences(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's preferences"""
    user = db.query(User).filter(User.id == current_user.id).first()
    return UserPreferencesResponse(
        daily_word_goal=user.daily_word_goal,
        writing_reminder_time=user.writing_reminder_time,
        theme_preferences=user.theme_preferences,
        ai_features_enabled=user.ai_features_enabled,
        timezone=user.timezone,
        locale=user.locale
    )

@router.put("/me/preferences", response_model=UserPreferencesResponse, status_code=status.HTTP_200_OK)
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's preferences"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update only valid preference fields
    update_data = preferences.dict(exclude_unset=True)
    updated_user = update_user(db, user, update_data)
    
    return UserPreferencesResponse(
        daily_word_goal=updated_user.daily_word_goal,
        writing_reminder_time=updated_user.writing_reminder_time,
        theme_preferences=updated_user.theme_preferences,
        ai_features_enabled=updated_user.ai_features_enabled,
        timezone=updated_user.timezone,
        locale=updated_user.locale
    ) 