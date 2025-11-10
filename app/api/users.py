from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.user_preferences import UserPreferencesResponse, UserPreferencesUpdate, PrivacySettings, PrivacyTierUpdate
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
    update_data = user_update.model_dump(exclude_unset=True)
    updated_user = update_user(db, user, update_data)
    return UserResponse.model_validate(updated_user)

@router.get("/me/stats", response_model=UserWritingStats, status_code=status.HTTP_200_OK)
async def get_user_stats(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 30
):
    """Get user's writing statistics (encrypted architecture - stats computed client-side)"""
    return UserWritingStats(
        total_logs=0,
        recent_logs=0,
        total_words=0,
        avg_words_per_entry=0.0,
        writing_streak=0,
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
    update_data = preferences.model_dump(exclude_unset=True)
    updated_user = update_user(db, user, update_data)
    
    return UserPreferencesResponse(
        daily_word_goal=updated_user.daily_word_goal,
        writing_reminder_time=updated_user.writing_reminder_time,
        theme_preferences=updated_user.theme_preferences,
        ai_features_enabled=updated_user.ai_features_enabled,
        timezone=updated_user.timezone,
        locale=updated_user.locale
    )

@router.get("/me/privacy", response_model=PrivacySettings, status_code=status.HTTP_200_OK)
async def get_privacy_settings(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's privacy tier settings"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_tier = user.privacy_tier or 'local_only'
    sync_enabled = current_tier in ['analytics_sync', 'full_sync']

    features_available = {
        "local_storage": True,
        "local_themes": True,
        "local_search": True,
        "cloud_sync": current_tier == 'full_sync',
        "cross_device_search": current_tier == 'full_sync',
        "encrypted_backup": current_tier == 'full_sync',
        "analytics_sync": current_tier in ['analytics_sync', 'full_sync']
    }

    return PrivacySettings(
        current_tier=current_tier,
        sync_enabled=sync_enabled,
        sync_enabled_at=user.sync_enabled_at,
        features_available=features_available
    )

@router.put("/me/privacy", response_model=PrivacySettings, status_code=status.HTTP_200_OK)
async def update_privacy_tier(
    tier_update: PrivacyTierUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's privacy tier (opt into cloud sync features)"""
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_tier = user.privacy_tier or 'local_only'
    new_tier = tier_update.privacy_tier

    tier_levels = {'local_only': 0, 'analytics_sync': 1, 'full_sync': 2}

    if tier_levels[new_tier] < tier_levels[current_tier]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot downgrade tier directly. Use DELETE /api/users/me/privacy/revoke to downgrade to local_only"
        )

    if new_tier != 'local_only' and not tier_update.he_public_key:
        raise HTTPException(
            status_code=400,
            detail="HE public key required for analytics_sync and full_sync tiers"
        )

    user.privacy_tier = new_tier
    user.he_public_key = tier_update.he_public_key

    if not user.sync_enabled_at and new_tier != 'local_only':
        user.sync_enabled_at = tier_update.consent_timestamp

    db.commit()
    db.refresh(user)

    sync_enabled = new_tier in ['analytics_sync', 'full_sync']
    features_available = {
        "local_storage": True,
        "local_themes": True,
        "local_search": True,
        "cloud_sync": new_tier == 'full_sync',
        "cross_device_search": new_tier == 'full_sync',
        "encrypted_backup": new_tier == 'full_sync',
        "analytics_sync": new_tier in ['analytics_sync', 'full_sync']
    }

    return PrivacySettings(
        current_tier=new_tier,
        sync_enabled=sync_enabled,
        sync_enabled_at=user.sync_enabled_at,
        features_available=features_available
    )

@router.delete("/me/privacy/revoke", response_model=dict, status_code=status.HTTP_200_OK)
async def revoke_cloud_sync(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke cloud sync access and delete all cloud data (downgrade to local-only)"""
    from app.models.models import EncryptedMetric, EncryptedBackup

    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    deleted_metrics = db.query(EncryptedMetric).filter(
        EncryptedMetric.user_id == current_user.id
    ).delete()

    deleted_backups = db.query(EncryptedBackup).filter(
        EncryptedBackup.user_id == current_user.id
    ).delete()

    user.privacy_tier = 'local_only'
    user.he_public_key = None
    user.sync_enabled_at = None

    db.commit()

    return {
        "message": "Cloud sync revoked successfully. All cloud data deleted.",
        "deleted_metrics": deleted_metrics,
        "deleted_backups": deleted_backups,
        "new_tier": "local_only"
    } 
