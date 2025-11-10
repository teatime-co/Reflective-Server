import pytest
from datetime import datetime, timedelta
from app.services.sync_service import SyncService
from app.models.models import EncryptedBackup, SyncConflict, User
from sqlalchemy.orm import Session
import uuid
import base64


@pytest.fixture
def sync_service():
    return SyncService()


@pytest.fixture
def sample_user(db: Session):
    """Create a sample user for testing"""
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="hashed_password",
        display_name="Test User",
        privacy_tier='full_sync',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_backup_data(sample_user):
    """Create sample backup data dict"""
    return {
        'id': str(uuid.uuid4()),
        'encrypted_content': base64.b64encode(b"test encrypted content").decode(),
        'content_iv': 'test_iv_123',
        'content_tag': 'test_tag_456',
        'encrypted_embedding': base64.b64encode(b"test encrypted embedding").decode(),
        'embedding_iv': 'embedding_iv_789',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'device_id': 'device-1'
    }


@pytest.fixture
def existing_backup(db: Session, sample_user):
    """Create an existing backup in the database"""
    backup = EncryptedBackup(
        id=str(uuid.uuid4()),
        user_id=sample_user.id,
        encrypted_content=b"existing encrypted content",
        content_iv="existing_iv",
        content_tag="existing_tag",
        encrypted_embedding=b"existing encrypted embedding",
        embedding_iv="existing_embedding_iv",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        device_id="device-1"
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)
    return backup


class TestSyncServiceBackupOperations:
    """Test backup storage, retrieval, and deletion operations"""

    def test_store_encrypted_backup_new(self, sync_service, db: Session, sample_user, sample_backup_data):
        """Test storing a new encrypted backup"""
        backup, conflict = sync_service.store_encrypted_backup(
            db=db,
            user_id=sample_user.id,
            backup_data=sample_backup_data
        )

        assert backup is not None
        assert conflict is None
        assert backup.id == sample_backup_data['id']
        assert backup.user_id == sample_user.id
        assert backup.device_id == 'device-1'

    def test_store_backup_update_existing_same_device(self, sync_service, db: Session, sample_user, existing_backup):
        """Test updating existing backup from same device (no conflict)"""
        updated_data = {
            'id': existing_backup.id,
            'encrypted_content': base64.b64encode(b"updated content").decode(),
            'content_iv': 'updated_iv',
            'content_tag': 'updated_tag',
            'encrypted_embedding': base64.b64encode(b"updated embedding").decode(),
            'embedding_iv': 'updated_embedding_iv',
            'created_at': existing_backup.created_at,
            'updated_at': datetime.utcnow(),
            'device_id': existing_backup.device_id
        }

        backup, conflict = sync_service.store_encrypted_backup(
            db=db,
            user_id=sample_user.id,
            backup_data=updated_data
        )

        assert backup is not None
        assert conflict is None
        assert backup.id == existing_backup.id
        assert backup.content_iv == 'updated_iv'

    def test_store_backup_with_embedding(self, sync_service, db: Session, sample_user, sample_backup_data):
        """Test storing backup with encrypted embedding"""
        backup, conflict = sync_service.store_encrypted_backup(
            db=db,
            user_id=sample_user.id,
            backup_data=sample_backup_data
        )

        assert backup.encrypted_embedding is not None
        assert backup.embedding_iv is not None

    def test_fetch_backups_since_timestamp(self, sync_service, db: Session, sample_user):
        """Test fetching backups since a specific timestamp"""
        now = datetime.utcnow()

        backup1_data = {
            'id': str(uuid.uuid4()),
            'encrypted_content': base64.b64encode(b"content1").decode(),
            'content_iv': 'iv1',
            'created_at': now - timedelta(days=5),
            'updated_at': now - timedelta(days=5),
            'device_id': 'device-1'
        }

        backup2_data = {
            'id': str(uuid.uuid4()),
            'encrypted_content': base64.b64encode(b"content2").decode(),
            'content_iv': 'iv2',
            'created_at': now - timedelta(days=2),
            'updated_at': now - timedelta(days=2),
            'device_id': 'device-1'
        }

        sync_service.store_encrypted_backup(db, sample_user.id, backup1_data)
        sync_service.store_encrypted_backup(db, sample_user.id, backup2_data)

        since = now - timedelta(days=3)
        backups = sync_service.fetch_backups_since(
            db=db,
            user_id=sample_user.id,
            since_timestamp=since
        )

        assert len(backups) == 1
        assert backups[0].id == backup2_data['id']

    def test_fetch_backups_exclude_device(self, sync_service, db: Session, sample_user):
        """Test fetching backups excluding specific device"""
        backup1_data = {
            'id': str(uuid.uuid4()),
            'encrypted_content': base64.b64encode(b"content1").decode(),
            'content_iv': 'iv1',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'device_id': 'device-1'
        }

        backup2_data = {
            'id': str(uuid.uuid4()),
            'encrypted_content': base64.b64encode(b"content2").decode(),
            'content_iv': 'iv2',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'device_id': 'device-2'
        }

        sync_service.store_encrypted_backup(db, sample_user.id, backup1_data)
        sync_service.store_encrypted_backup(db, sample_user.id, backup2_data)

        backups = sync_service.fetch_backups_since(
            db=db,
            user_id=sample_user.id,
            exclude_device_id='device-1'
        )

        assert len(backups) == 1
        assert backups[0].device_id == 'device-2'

    def test_fetch_backups_pagination_limit(self, sync_service, db: Session, sample_user):
        """Test pagination limit for fetching backups"""
        for i in range(10):
            backup_data = {
                'id': str(uuid.uuid4()),
                'encrypted_content': base64.b64encode(f"content{i}".encode()).decode(),
                'content_iv': f'iv{i}',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'device_id': 'device-1'
            }
            sync_service.store_encrypted_backup(db, sample_user.id, backup_data)

        backups = sync_service.fetch_backups_since(
            db=db,
            user_id=sample_user.id,
            limit=5
        )

        assert len(backups) == 5

    def test_delete_backup_success(self, sync_service, db: Session, sample_user, existing_backup):
        """Test deleting an existing backup"""
        deleted = sync_service.delete_backup(
            db=db,
            backup_id=existing_backup.id,
            user_id=sample_user.id
        )

        assert deleted is True

        backup = db.query(EncryptedBackup).filter(EncryptedBackup.id == existing_backup.id).first()
        assert backup is None

    def test_delete_backup_not_found(self, sync_service, db: Session, sample_user):
        """Test deleting a non-existent backup"""
        deleted = sync_service.delete_backup(
            db=db,
            backup_id=str(uuid.uuid4()),
            user_id=sample_user.id
        )

        assert deleted is False

    def test_delete_all_backups_for_user(self, sync_service, db: Session, sample_user):
        """Test deleting all backups for a user (privacy tier downgrade)"""
        for i in range(5):
            backup_data = {
                'id': str(uuid.uuid4()),
                'encrypted_content': base64.b64encode(f"content{i}".encode()).decode(),
                'content_iv': f'iv{i}',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'device_id': 'device-1'
            }
            sync_service.store_encrypted_backup(db, sample_user.id, backup_data)

        count = sync_service.delete_all_backups(db, sample_user.id)

        assert count == 5

        backups = db.query(EncryptedBackup).filter(EncryptedBackup.user_id == sample_user.id).all()
        assert len(backups) == 0


class TestSyncServiceConflictDetection:
    """Test conflict detection logic"""

    def test_detect_conflict_different_timestamps_different_devices(self, sync_service, existing_backup):
        """Test conflict detection with different timestamps and devices"""
        local_data = {
            'id': existing_backup.id,
            'encrypted_content': base64.b64encode(b"local content").decode(),
            'content_iv': 'local_iv',
            'updated_at': datetime.utcnow() + timedelta(minutes=5),
            'device_id': 'device-2'
        }

        conflict = sync_service.detect_conflict(local_data, existing_backup)

        assert conflict is True

    def test_no_conflict_same_device(self, sync_service, existing_backup):
        """Test no conflict when update is from same device"""
        local_data = {
            'id': existing_backup.id,
            'encrypted_content': base64.b64encode(b"updated content").decode(),
            'content_iv': 'updated_iv',
            'updated_at': datetime.utcnow() + timedelta(minutes=5),
            'device_id': existing_backup.device_id
        }

        conflict = sync_service.detect_conflict(local_data, existing_backup)

        assert conflict is False

    def test_no_conflict_same_timestamp(self, sync_service, existing_backup):
        """Test no conflict when timestamps match"""
        local_data = {
            'id': existing_backup.id,
            'encrypted_content': base64.b64encode(b"same content").decode(),
            'content_iv': 'same_iv',
            'updated_at': existing_backup.updated_at,
            'device_id': 'device-2'
        }

        conflict = sync_service.detect_conflict(local_data, existing_backup)

        assert conflict is False

    def test_create_conflict_record(self, sync_service, db: Session, sample_user, existing_backup):
        """Test creating a conflict record"""
        local_data = {
            'id': existing_backup.id,
            'encrypted_content': base64.b64encode(b"local content").decode(),
            'content_iv': 'local_iv',
            'updated_at': datetime.utcnow() + timedelta(minutes=5),
            'device_id': 'device-2'
        }

        conflict = sync_service.create_conflict_record(
            db=db,
            user_id=sample_user.id,
            log_id=existing_backup.id,
            local_data=local_data,
            remote_data=existing_backup
        )

        assert conflict is not None
        assert conflict.log_id == existing_backup.id
        assert conflict.local_device_id == 'device-2'
        assert conflict.remote_device_id == existing_backup.device_id
        assert conflict.resolved is False

    def test_conflict_includes_device_metadata(self, sync_service, db: Session, sample_user, existing_backup):
        """Test that conflict record includes device metadata"""
        local_data = {
            'id': existing_backup.id,
            'encrypted_content': base64.b64encode(b"local content").decode(),
            'content_iv': 'local_iv',
            'updated_at': datetime.utcnow(),
            'device_id': 'device-2'
        }

        conflict = sync_service.create_conflict_record(
            db=db,
            user_id=sample_user.id,
            log_id=existing_backup.id,
            local_data=local_data,
            remote_data=existing_backup
        )

        assert conflict.local_device_id is not None
        assert conflict.remote_device_id is not None
        assert conflict.detected_at is not None


class TestSyncServiceConflictResolution:
    """Test conflict resolution operations"""

    @pytest.fixture
    def sample_conflict(self, db: Session, sample_user, existing_backup):
        """Create a sample conflict"""
        conflict = SyncConflict(
            user_id=sample_user.id,
            log_id=existing_backup.id,
            local_encrypted_content=b"local content",
            local_iv="local_iv",
            local_updated_at=datetime.utcnow(),
            local_device_id="device-2",
            remote_encrypted_content=existing_backup.encrypted_content,
            remote_iv=existing_backup.content_iv,
            remote_updated_at=existing_backup.updated_at,
            remote_device_id=existing_backup.device_id,
            detected_at=datetime.utcnow()
        )
        db.add(conflict)
        db.commit()
        db.refresh(conflict)
        return conflict

    def test_resolve_conflict_choose_local(self, sync_service, db: Session, sample_user, existing_backup, sample_conflict):
        """Test resolving conflict by choosing local version"""
        resolution = {
            'chosen_version': 'local'
        }

        backup = sync_service.resolve_conflict(
            db=db,
            conflict_id=sample_conflict.id,
            user_id=sample_user.id,
            resolution=resolution
        )

        assert backup is not None
        assert backup.encrypted_content == sample_conflict.local_encrypted_content
        assert backup.content_iv == sample_conflict.local_iv

        db.refresh(sample_conflict)
        assert sample_conflict.resolved is True

    def test_resolve_conflict_choose_remote(self, sync_service, db: Session, sample_user, existing_backup, sample_conflict):
        """Test resolving conflict by keeping remote version"""
        resolution = {
            'chosen_version': 'remote'
        }

        backup = sync_service.resolve_conflict(
            db=db,
            conflict_id=sample_conflict.id,
            user_id=sample_user.id,
            resolution=resolution
        )

        assert backup is not None
        assert backup.encrypted_content == existing_backup.encrypted_content

        db.refresh(sample_conflict)
        assert sample_conflict.resolved is True

    def test_resolve_conflict_with_merged_version(self, sync_service, db: Session, sample_user, existing_backup, sample_conflict):
        """Test resolving conflict with merged version"""
        resolution = {
            'chosen_version': 'merged',
            'final_encrypted_content': base64.b64encode(b"merged content").decode(),
            'final_iv': 'merged_iv',
            'final_encrypted_embedding': base64.b64encode(b"merged embedding").decode(),
            'final_embedding_iv': 'merged_embedding_iv'
        }

        backup = sync_service.resolve_conflict(
            db=db,
            conflict_id=sample_conflict.id,
            user_id=sample_user.id,
            resolution=resolution
        )

        assert backup is not None
        assert b"merged content" == backup.encrypted_content
        assert backup.content_iv == 'merged_iv'

        db.refresh(sample_conflict)
        assert sample_conflict.resolved is True

    def test_get_unresolved_conflicts(self, sync_service, db: Session, sample_user, sample_conflict):
        """Test fetching unresolved conflicts"""
        conflicts = sync_service.get_unresolved_conflicts(
            db=db,
            user_id=sample_user.id
        )

        assert len(conflicts) == 1
        assert conflicts[0].id == sample_conflict.id
        assert conflicts[0].resolved is False

    def test_resolve_marks_conflict_resolved_with_timestamp(self, sync_service, db: Session, sample_user, existing_backup, sample_conflict):
        """Test that resolving sets resolved flag and timestamp"""
        resolution = {
            'chosen_version': 'local'
        }

        sync_service.resolve_conflict(
            db=db,
            conflict_id=sample_conflict.id,
            user_id=sample_user.id,
            resolution=resolution
        )

        db.refresh(sample_conflict)
        assert sample_conflict.resolved is True
        assert sample_conflict.resolved_at is not None

    def test_resolve_conflict_not_found(self, sync_service, db: Session, sample_user):
        """Test resolving non-existent conflict"""
        resolution = {
            'chosen_version': 'local'
        }

        backup = sync_service.resolve_conflict(
            db=db,
            conflict_id=uuid.uuid4(),
            user_id=sample_user.id,
            resolution=resolution
        )

        assert backup is None
