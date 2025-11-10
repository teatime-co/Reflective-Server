"""
Sync API Endpoints

Handles encrypted backup upload, fetch, delete, and conflict resolution.
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
import base64

from ..database import get_db
from app.api.auth import get_current_user
from ..schemas.user import UserResponse
from ..schemas.encrypted_data import (
    EncryptedBackupData,
    EncryptedBackupResponse,
    EncryptedBackupList,
    ConflictList,
    SyncConflict as SyncConflictSchema,
    ConflictVersion,
    ConflictResolution,
    EncryptionStatusResponse
)
from ..services.sync_service import SyncService
from ..models.models import EncryptedBackup

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/backup", response_model=EncryptedBackupResponse, status_code=status.HTTP_201_CREATED)
async def upload_encrypted_backup(
    backup_data: EncryptedBackupData,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload encrypted backup for cross-device sync.

    Privacy tier requirements:
    - local_only: REJECTED (403)
    - analytics_sync: REJECTED (403)
    - full_sync: ALLOWED

    Args:
        backup_data: Encrypted content + metadata
        current_user: Authenticated user
        db: Database session

    Returns:
        EncryptedBackupResponse: Upload confirmation

    Raises:
        403: User's privacy tier does not allow full sync
        409: Conflict detected (client should fetch conflicts endpoint)
    """
    if current_user.privacy_tier != 'full_sync':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Full sync not enabled. Upgrade privacy tier to 'full_sync' to upload backups."
        )

    try:
        backup_dict = {
            'id': backup_data.id,
            'encrypted_content': backup_data.encrypted_content,
            'content_iv': backup_data.content_iv,
            'content_tag': backup_data.content_tag,
            'encrypted_embedding': backup_data.encrypted_embedding,
            'embedding_iv': backup_data.embedding_iv,
            'created_at': backup_data.created_at,
            'updated_at': backup_data.updated_at,
            'device_id': backup_data.device_id
        }

        backup, conflict = SyncService.store_encrypted_backup(
            db=db,
            user_id=current_user.id,
            backup_data=backup_dict
        )

        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Sync conflict detected. Fetch conflicts to resolve.",
                    "conflict_id": str(conflict.id),
                    "log_id": conflict.log_id
                }
            )

        return EncryptedBackupResponse(
            id=backup.id,
            user_id=str(backup.user_id),
            created_at=backup.created_at,
            updated_at=backup.updated_at,
            device_id=backup.device_id,
            message="Backup stored successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store encrypted backup: {str(e)}"
        )


@router.get("/backups", response_model=EncryptedBackupList, status_code=status.HTTP_200_OK)
async def fetch_encrypted_backups(
    since: Optional[datetime] = Query(None, description="Fetch backups updated after this timestamp"),
    device_id: Optional[str] = Query(None, description="Exclude backups from this device"),
    limit: int = Query(100, ge=1, le=500, description="Max number of backups to fetch"),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch encrypted backups for sync.

    Args:
        since: Optional timestamp to fetch only recent backups
        device_id: Optional device ID to exclude (avoid self-sync)
        limit: Max backups to return (default 100, max 500)
        current_user: Authenticated user
        db: Database session

    Returns:
        EncryptedBackupList: List of encrypted backups with metadata

    Raises:
        403: User's privacy tier does not allow full sync
    """
    if current_user.privacy_tier != 'full_sync':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Full sync not enabled. Upgrade privacy tier to 'full_sync'."
        )

    try:
        backups = SyncService.fetch_backups_since(
            db=db,
            user_id=current_user.id,
            since_timestamp=since,
            exclude_device_id=device_id,
            limit=limit
        )

        backup_list = []
        for backup in backups:
            backup_list.append(EncryptedBackupData(
                id=backup.id,
                encrypted_content=base64.b64encode(backup.encrypted_content).decode('utf-8'),
                content_iv=backup.content_iv,
                content_tag=backup.content_tag,
                encrypted_embedding=base64.b64encode(backup.encrypted_embedding).decode('utf-8') if backup.encrypted_embedding else None,
                embedding_iv=backup.embedding_iv,
                created_at=backup.created_at,
                updated_at=backup.updated_at,
                device_id=backup.device_id
            ))

        has_more = len(backups) == limit

        return EncryptedBackupList(
            backups=backup_list,
            has_more=has_more,
            total_count=len(backup_list)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch encrypted backups: {str(e)}"
        )


@router.delete("/backup/{backup_id}", response_model=EncryptionStatusResponse, status_code=status.HTTP_200_OK)
async def delete_encrypted_backup(
    backup_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete encrypted backup by ID.

    Args:
        backup_id: Backup ID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        EncryptionStatusResponse: Deletion confirmation

    Raises:
        404: Backup not found
    """
    deleted = SyncService.delete_backup(
        db=db,
        backup_id=backup_id,
        user_id=current_user.id
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backup {backup_id} not found or does not belong to user"
        )

    return EncryptionStatusResponse(
        success=True,
        message="Backup deleted successfully",
        details={"backup_id": backup_id}
    )


@router.get("/conflicts", response_model=ConflictList, status_code=status.HTTP_200_OK)
async def get_sync_conflicts(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get unresolved sync conflicts for user resolution.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        ConflictList: List of unresolved conflicts with both versions

    Raises:
        403: User's privacy tier does not allow full sync
    """
    if current_user.privacy_tier != 'full_sync':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Full sync not enabled."
        )

    try:
        conflicts = SyncService.get_unresolved_conflicts(
            db=db,
            user_id=current_user.id
        )

        conflict_list = []
        for conflict in conflicts:
            conflict_list.append(SyncConflictSchema(
                id=str(conflict.id),
                log_id=conflict.log_id,
                local_version=ConflictVersion(
                    encrypted_content=base64.b64encode(conflict.local_encrypted_content).decode('utf-8'),
                    iv=conflict.local_iv,
                    updated_at=conflict.local_updated_at,
                    device_id=conflict.local_device_id
                ),
                remote_version=ConflictVersion(
                    encrypted_content=base64.b64encode(conflict.remote_encrypted_content).decode('utf-8'),
                    iv=conflict.remote_iv,
                    updated_at=conflict.remote_updated_at,
                    device_id=conflict.remote_device_id
                ),
                detected_at=conflict.detected_at
            ))

        return ConflictList(
            conflicts=conflict_list,
            total_count=len(conflict_list)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conflicts: {str(e)}"
        )


@router.post("/conflicts/{conflict_id}/resolve", response_model=EncryptionStatusResponse, status_code=status.HTTP_200_OK)
async def resolve_sync_conflict(
    conflict_id: str,
    resolution: ConflictResolution,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resolve sync conflict based on user's choice.

    Args:
        conflict_id: Conflict UUID
        resolution: User's resolution (chosen_version + optional merged data)
        current_user: Authenticated user
        db: Database session

    Returns:
        EncryptionStatusResponse: Resolution confirmation

    Raises:
        404: Conflict not found
        422: Merged version missing required data
    """
    if resolution.chosen_version == 'merged':
        if not resolution.final_encrypted_content or not resolution.final_iv:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Merged version requires final_encrypted_content and final_iv"
            )

    try:
        import uuid as uuid_lib
        conflict_uuid = uuid_lib.UUID(conflict_id)

        backup = SyncService.resolve_conflict(
            db=db,
            conflict_id=conflict_uuid,
            user_id=current_user.id,
            resolution=resolution.model_dump()
        )

        if not backup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conflict {conflict_id} not found"
            )

        return EncryptionStatusResponse(
            success=True,
            message="Conflict resolved successfully",
            details={
                "conflict_id": conflict_id,
                "log_id": backup.id,
                "chosen_version": resolution.chosen_version
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}"
        )
