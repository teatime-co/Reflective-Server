import pytest
from typing import Optional
from fastapi import status
from datetime import datetime, timedelta
import base64
import uuid
from app.models.models import User, EncryptedBackup, SyncConflict


def create_test_backup(log_id: Optional[str] = None, device_id: str = "device-1"):
    """Helper function to create test backup data"""
    if log_id is None:
        log_id = str(uuid.uuid4())

    return {
        "id": log_id,
        "encrypted_content": base64.b64encode(b"test encrypted content").decode(),
        "content_iv": f"iv_{uuid.uuid4()}",
        "content_tag": "test_tag",
        "encrypted_embedding": base64.b64encode(b"test encrypted embedding").decode(),
        "embedding_iv": f"embedding_iv_{uuid.uuid4()}",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "device_id": device_id
    }


class TestUploadBackup:
    """Tests for POST /api/sync/backup endpoint"""

    def test_upload_encrypted_backup_success(self, client, test_user, db):
        """Test successfully uploading an encrypted backup"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        backup_data = create_test_backup()

        response = client.post(
            "/api/sync/backup",
            headers=test_user["headers"],
            json=backup_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == backup_data["id"]
        assert data["device_id"] == "device-1"
        assert "Backup stored successfully" in data["message"]

    def test_upload_backup_privacy_tier_validation_403(self, client, test_user, db):
        """Test that non-full_sync users get 403"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'local_only'
        db.commit()

        backup_data = create_test_backup()

        response = client.post(
            "/api/sync/backup",
            headers=test_user["headers"],
            json=backup_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Full sync not enabled" in response.json()["detail"]

    def test_upload_backup_analytics_sync_forbidden(self, client, test_user, db):
        """Test that analytics_sync tier also gets 403"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'analytics_sync'
        db.commit()

        backup_data = create_test_backup()

        response = client.post(
            "/api/sync/backup",
            headers=test_user["headers"],
            json=backup_data
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_backup_returns_409_on_conflict(self, client, test_user, db):
        """Test that conflicting backup returns 409"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        log_id = str(uuid.uuid4())
        backup1 = create_test_backup(log_id=log_id, device_id="device-1")

        client.post("/api/sync/backup", headers=test_user["headers"], json=backup1)

        backup2 = create_test_backup(log_id=log_id, device_id="device-2")
        backup2["updated_at"] = (datetime.utcnow() + timedelta(seconds=5)).isoformat() + "Z"

        response = client.post(
            "/api/sync/backup",
            headers=test_user["headers"],
            json=backup2
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_upload_backup_conflict_includes_details(self, client, test_user, db):
        """Test that conflict response includes conflict ID and log ID"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        log_id = str(uuid.uuid4())
        backup1 = create_test_backup(log_id=log_id, device_id="device-1")
        client.post("/api/sync/backup", headers=test_user["headers"], json=backup1)

        backup2 = create_test_backup(log_id=log_id, device_id="device-2")
        backup2["updated_at"] = (datetime.utcnow() + timedelta(seconds=5)).isoformat() + "Z"

        response = client.post(
            "/api/sync/backup",
            headers=test_user["headers"],
            json=backup2
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()["detail"]
        assert "conflict_id" in data
        assert "log_id" in data
        assert data["log_id"] == log_id


class TestFetchBackups:
    """Tests for GET /api/sync/backups endpoint"""

    def test_fetch_backups_success(self, client, test_user, db):
        """Test fetching backups successfully"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        for i in range(3):
            backup = create_test_backup()
            client.post("/api/sync/backup", headers=test_user["headers"], json=backup)

        response = client.get(
            "/api/sync/backups",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["backups"]) == 3
        assert "has_more" in data

    def test_fetch_backups_since_timestamp_filter(self, client, test_user, db):
        """Test filtering backups by timestamp"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        now = datetime.utcnow()

        old_backup = create_test_backup()
        old_backup["updated_at"] = (now - timedelta(days=5)).isoformat() + "Z"
        client.post("/api/sync/backup", headers=test_user["headers"], json=old_backup)

        new_backup = create_test_backup()
        new_backup["updated_at"] = (now - timedelta(days=1)).isoformat() + "Z"
        client.post("/api/sync/backup", headers=test_user["headers"], json=new_backup)

        since = (now - timedelta(days=2)).isoformat()
        response = client.get(
            f"/api/sync/backups?since={since}",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["backups"]) == 1

    def test_fetch_backups_exclude_device_id(self, client, test_user, db):
        """Test excluding backups from specific device"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        backup1 = create_test_backup(device_id="device-1")
        backup2 = create_test_backup(device_id="device-2")

        client.post("/api/sync/backup", headers=test_user["headers"], json=backup1)
        client.post("/api/sync/backup", headers=test_user["headers"], json=backup2)

        response = client.get(
            "/api/sync/backups?device_id=device-1",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["backups"]) == 1
        assert data["backups"][0]["device_id"] == "device-2"

    def test_fetch_backups_pagination_limit(self, client, test_user, db):
        """Test pagination limit parameter"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        for i in range(10):
            backup = create_test_backup()
            client.post("/api/sync/backup", headers=test_user["headers"], json=backup)

        response = client.get(
            "/api/sync/backups?limit=5",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["backups"]) == 5

    def test_fetch_backups_has_more_indicator(self, client, test_user, db):
        """Test has_more indicator for pagination"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        for i in range(10):
            backup = create_test_backup()
            client.post("/api/sync/backup", headers=test_user["headers"], json=backup)

        response = client.get(
            "/api/sync/backups?limit=10",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_more"] is True

    def test_fetch_backups_user_isolation(self, client, test_user, test_user2, db):
        """Test that users can only see their own backups"""
        for user in [test_user, test_user2]:
            db_user = db.query(User).filter(User.id == user["user"].id).first()
            db_user.privacy_tier = 'full_sync'
        db.commit()

        user1_backup = create_test_backup()
        client.post("/api/sync/backup", headers=test_user["headers"], json=user1_backup)

        user2_backup = create_test_backup()
        client.post("/api/sync/backup", headers=test_user2["headers"], json=user2_backup)

        response = client.get(
            "/api/sync/backups",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["backups"]) == 1
        assert data["backups"][0]["id"] == user1_backup["id"]

    def test_fetch_backups_privacy_tier_validation(self, client, test_user, db):
        """Test that non-full_sync users get 403"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'local_only'
        db.commit()

        response = client.get(
            "/api/sync/backups",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDeleteBackup:
    """Tests for DELETE /api/sync/backup/{backup_id} endpoint"""

    def test_delete_backup_success(self, client, test_user, db):
        """Test deleting a backup successfully"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        backup = create_test_backup()
        client.post("/api/sync/backup", headers=test_user["headers"], json=backup)

        response = client.delete(
            f"/api/sync/backup/{backup['id']}",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "Backup deleted successfully" in data["message"]

    def test_delete_backup_not_found_404(self, client, test_user):
        """Test deleting non-existent backup returns 404"""
        response = client.delete(
            f"/api/sync/backup/{uuid.uuid4()}",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_backup_user_isolation(self, client, test_user, test_user2, db):
        """Test users cannot delete other users' backups"""
        for user in [test_user, test_user2]:
            db_user = db.query(User).filter(User.id == user["user"].id).first()
            db_user.privacy_tier = 'full_sync'
        db.commit()

        backup = create_test_backup()
        client.post("/api/sync/backup", headers=test_user["headers"], json=backup)

        response = client.delete(
            f"/api/sync/backup/{backup['id']}",
            headers=test_user2["headers"]
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSyncConflicts:
    """Tests for conflict endpoints"""

    @pytest.fixture
    def setup_conflict(self, client, test_user, db):
        """Create a conflict scenario"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        log_id = str(uuid.uuid4())

        backup1 = create_test_backup(log_id=log_id, device_id="device-1")
        client.post("/api/sync/backup", headers=test_user["headers"], json=backup1)

        backup2 = create_test_backup(log_id=log_id, device_id="device-2")
        backup2["updated_at"] = (datetime.utcnow() + timedelta(seconds=5)).isoformat() + "Z"
        client.post("/api/sync/backup", headers=test_user["headers"], json=backup2)

        return log_id

    def test_get_sync_conflicts_returns_unresolved(self, client, test_user, db, setup_conflict):
        """Test fetching unresolved conflicts"""
        response = client.get(
            "/api/sync/conflicts",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conflicts"]) == 1
        assert data["conflicts"][0]["log_id"] == setup_conflict

    def test_get_conflicts_empty_when_none(self, client, test_user, db):
        """Test fetching conflicts when none exist"""
        db_user = db.query(User).filter(User.id == test_user["user"].id).first()
        db_user.privacy_tier = 'full_sync'
        db.commit()

        response = client.get(
            "/api/sync/conflicts",
            headers=test_user["headers"]
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["conflicts"]) == 0

    def test_conflicts_include_both_versions(self, client, test_user, db, setup_conflict):
        """Test that conflicts include local and remote versions"""
        response = client.get(
            "/api/sync/conflicts",
            headers=test_user["headers"]
        )

        data = response.json()
        conflict = data["conflicts"][0]

        assert "local_version" in conflict
        assert "remote_version" in conflict
        assert "encrypted_content" in conflict["local_version"]
        assert "encrypted_content" in conflict["remote_version"]

    def test_resolve_conflict_local_version(self, client, test_user, db, setup_conflict):
        """Test resolving conflict by choosing local version"""
        conflicts = client.get("/api/sync/conflicts", headers=test_user["headers"]).json()
        conflict_id = conflicts["conflicts"][0]["id"]

        response = client.post(
            f"/api/sync/conflicts/{conflict_id}/resolve",
            headers=test_user["headers"],
            json={"chosen_version": "local"}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["details"]["chosen_version"] == "local"

    def test_resolve_conflict_remote_version(self, client, test_user, db, setup_conflict):
        """Test resolving conflict by choosing remote version"""
        conflicts = client.get("/api/sync/conflicts", headers=test_user["headers"]).json()
        conflict_id = conflicts["conflicts"][0]["id"]

        response = client.post(
            f"/api/sync/conflicts/{conflict_id}/resolve",
            headers=test_user["headers"],
            json={"chosen_version": "remote"}
        )

        assert response.status_code == status.HTTP_200_OK

    def test_resolve_conflict_merged_version(self, client, test_user, db, setup_conflict):
        """Test resolving conflict with merged version"""
        conflicts = client.get("/api/sync/conflicts", headers=test_user["headers"]).json()
        conflict_id = conflicts["conflicts"][0]["id"]

        response = client.post(
            f"/api/sync/conflicts/{conflict_id}/resolve",
            headers=test_user["headers"],
            json={
                "chosen_version": "merged",
                "final_encrypted_content": base64.b64encode(b"merged content").decode(),
                "final_iv": "merged_iv"
            }
        )

        assert response.status_code == status.HTTP_200_OK

    def test_resolve_conflict_validates_merged_fields_422(self, client, test_user, db, setup_conflict):
        """Test that merged version requires all fields"""
        conflicts = client.get("/api/sync/conflicts", headers=test_user["headers"]).json()
        conflict_id = conflicts["conflicts"][0]["id"]

        response = client.post(
            f"/api/sync/conflicts/{conflict_id}/resolve",
            headers=test_user["headers"],
            json={
                "chosen_version": "merged"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_resolve_conflict_not_found_404(self, client, test_user):
        """Test resolving non-existent conflict returns 404"""
        response = client.post(
            f"/api/sync/conflicts/{uuid.uuid4()}/resolve",
            headers=test_user["headers"],
            json={"chosen_version": "local"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_resolved_conflict_disappears_from_list(self, client, test_user, db, setup_conflict):
        """Test that resolved conflicts don't appear in GET /conflicts"""
        conflicts = client.get("/api/sync/conflicts", headers=test_user["headers"]).json()
        conflict_id = conflicts["conflicts"][0]["id"]

        client.post(
            f"/api/sync/conflicts/{conflict_id}/resolve",
            headers=test_user["headers"],
            json={"chosen_version": "local"}
        )

        response = client.get("/api/sync/conflicts", headers=test_user["headers"])
        data = response.json()
        assert len(data["conflicts"]) == 0
