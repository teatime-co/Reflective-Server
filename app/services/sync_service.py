"""
Sync Service

Handles encrypted backup/restore logic and conflict detection for cross-device sync.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
import base64
import uuid

from ..models.models import EncryptedBackup, SyncConflict, User


class SyncService:
    """Service for handling encrypted sync operations"""

    @staticmethod
    def store_encrypted_backup(
        db: Session,
        user_id: uuid.UUID,
        backup_data: Dict[str, Any]
    ) -> tuple[Optional[EncryptedBackup], Optional[SyncConflict]]:
        """
        Store encrypted backup, detecting conflicts with existing backups.

        Args:
            db: Database session
            user_id: User UUID
            backup_data: Dict with id, encrypted_content, content_iv, device_id, etc.

        Returns:
            Tuple of (EncryptedBackup, SyncConflict or None)
            - If no conflict: (backup, None)
            - If conflict detected: (None, conflict)
        """
        existing = db.query(EncryptedBackup).filter(
            EncryptedBackup.id == backup_data['id'],
            EncryptedBackup.user_id == user_id
        ).first()

        if existing:
            conflict = SyncService.detect_conflict(
                local_backup=backup_data,
                remote_backup=existing
            )

            if conflict:
                conflict_record = SyncService.create_conflict_record(
                    db=db,
                    user_id=user_id,
                    log_id=backup_data['id'],
                    local_data=backup_data,
                    remote_data=existing
                )
                return None, conflict_record
            else:
                existing.encrypted_content = base64.b64decode(backup_data['encrypted_content'])
                existing.content_iv = backup_data['content_iv']
                existing.content_tag = backup_data.get('content_tag')
                existing.updated_at = backup_data['updated_at']
                existing.device_id = backup_data['device_id']

                if backup_data.get('encrypted_embedding'):
                    existing.encrypted_embedding = base64.b64decode(backup_data['encrypted_embedding'])
                    existing.embedding_iv = backup_data.get('embedding_iv')

                db.commit()
                db.refresh(existing)
                return existing, None
        else:
            new_backup = EncryptedBackup(
                id=backup_data['id'],
                user_id=user_id,
                encrypted_content=base64.b64decode(backup_data['encrypted_content']),
                content_iv=backup_data['content_iv'],
                content_tag=backup_data.get('content_tag'),
                encrypted_embedding=base64.b64decode(backup_data['encrypted_embedding']) if backup_data.get('encrypted_embedding') else None,
                embedding_iv=backup_data.get('embedding_iv'),
                created_at=backup_data['created_at'],
                updated_at=backup_data['updated_at'],
                device_id=backup_data['device_id']
            )

            db.add(new_backup)
            db.commit()
            db.refresh(new_backup)
            return new_backup, None

    @staticmethod
    def detect_conflict(local_backup: Dict[str, Any], remote_backup: EncryptedBackup) -> bool:
        """
        Detect if local and remote versions conflict.

        Conflict occurs when:
        - Same log_id
        - Different updated_at timestamps
        - Different device_ids

        Args:
            local_backup: Dict from client
            remote_backup: Existing EncryptedBackup from DB

        Returns:
            True if conflict detected, False otherwise
        """
        if local_backup['id'] != remote_backup.id:
            return False

        if local_backup['updated_at'] != remote_backup.updated_at:
            if local_backup['device_id'] != remote_backup.device_id:
                return True

        return False

    @staticmethod
    def create_conflict_record(
        db: Session,
        user_id: uuid.UUID,
        log_id: str,
        local_data: Dict[str, Any],
        remote_data: EncryptedBackup
    ) -> SyncConflict:
        """
        Create sync conflict record for user resolution.

        Args:
            db: Database session
            user_id: User UUID
            log_id: Log entry ID
            local_data: Local version from client
            remote_data: Remote version from DB

        Returns:
            Created SyncConflict record
        """
        conflict = SyncConflict(
            user_id=user_id,
            log_id=log_id,
            local_encrypted_content=base64.b64decode(local_data['encrypted_content']),
            local_iv=local_data['content_iv'],
            local_tag=local_data.get('content_tag'),
            local_updated_at=local_data['updated_at'],
            local_device_id=local_data['device_id'],
            remote_encrypted_content=remote_data.encrypted_content,
            remote_iv=remote_data.content_iv,
            remote_tag=remote_data.content_tag,
            remote_updated_at=remote_data.updated_at,
            remote_device_id=remote_data.device_id,
            detected_at=datetime.utcnow()
        )

        db.add(conflict)
        db.commit()
        db.refresh(conflict)
        return conflict

    @staticmethod
    def fetch_backups_since(
        db: Session,
        user_id: uuid.UUID,
        since_timestamp: Optional[datetime] = None,
        exclude_device_id: Optional[str] = None,
        limit: int = 100
    ) -> list[EncryptedBackup]:
        """
        Fetch encrypted backups for sync.

        Args:
            db: Database session
            user_id: User UUID
            since_timestamp: Only fetch backups updated after this time
            exclude_device_id: Exclude backups from this device (avoid self-sync)
            limit: Max number of backups to return

        Returns:
            List of EncryptedBackup records
        """
        query = db.query(EncryptedBackup).filter(
            EncryptedBackup.user_id == user_id
        )

        if since_timestamp:
            query = query.filter(EncryptedBackup.updated_at > since_timestamp)

        if exclude_device_id:
            query = query.filter(EncryptedBackup.device_id != exclude_device_id)

        query = query.order_by(EncryptedBackup.updated_at.asc())
        query = query.limit(limit)

        return query.all()

    @staticmethod
    def delete_backup(
        db: Session,
        backup_id: str,
        user_id: uuid.UUID
    ) -> bool:
        """
        Delete encrypted backup by ID.

        Args:
            db: Database session
            backup_id: Backup ID to delete
            user_id: User UUID (for authorization)

        Returns:
            True if deleted, False if not found
        """
        backup = db.query(EncryptedBackup).filter(
            EncryptedBackup.id == backup_id,
            EncryptedBackup.user_id == user_id
        ).first()

        if not backup:
            return False

        db.delete(backup)
        db.commit()
        return True

    @staticmethod
    def delete_all_backups(db: Session, user_id: uuid.UUID) -> int:
        """
        Delete all encrypted backups for a user (privacy tier downgrade).

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            Number of backups deleted
        """
        count = db.query(EncryptedBackup).filter(
            EncryptedBackup.user_id == user_id
        ).delete()

        db.commit()
        return count

    @staticmethod
    def get_unresolved_conflicts(
        db: Session,
        user_id: uuid.UUID
    ) -> list[SyncConflict]:
        """
        Get all unresolved conflicts for a user.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            List of unresolved SyncConflict records
        """
        return db.query(SyncConflict).filter(
            SyncConflict.user_id == user_id,
            SyncConflict.resolved == False
        ).order_by(SyncConflict.detected_at.desc()).all()

    @staticmethod
    def resolve_conflict(
        db: Session,
        conflict_id: uuid.UUID,
        user_id: uuid.UUID,
        resolution: dict
    ) -> Optional[EncryptedBackup]:
        """
        Resolve sync conflict based on user's choice.

        Args:
            db: Database session
            conflict_id: Conflict UUID
            user_id: User UUID (for authorization)
            resolution: Dict with chosen_version and optional merged data

        Returns:
            Updated EncryptedBackup or None if conflict not found
        """
        conflict = db.query(SyncConflict).filter(
            SyncConflict.id == conflict_id,
            SyncConflict.user_id == user_id
        ).first()

        if not conflict:
            return None

        backup = db.query(EncryptedBackup).filter(
            EncryptedBackup.id == conflict.log_id,
            EncryptedBackup.user_id == user_id
        ).first()

        if not backup:
            return None

        chosen_version = resolution['chosen_version']

        if chosen_version == 'local':
            backup.encrypted_content = conflict.local_encrypted_content
            backup.content_iv = conflict.local_iv
            backup.updated_at = conflict.local_updated_at
            backup.device_id = conflict.local_device_id
        elif chosen_version == 'remote':
            pass
        elif chosen_version == 'merged':
            backup.encrypted_content = base64.b64decode(resolution['final_encrypted_content'])
            backup.content_iv = resolution['final_iv']
            backup.updated_at = datetime.utcnow()
            if resolution.get('final_encrypted_embedding'):
                backup.encrypted_embedding = base64.b64decode(resolution['final_encrypted_embedding'])
                backup.embedding_iv = resolution.get('final_embedding_iv')

        conflict.resolved = True
        conflict.resolved_at = datetime.utcnow()

        db.commit()
        db.refresh(backup)
        return backup
