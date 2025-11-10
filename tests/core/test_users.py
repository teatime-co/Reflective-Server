import pytest
from fastapi import status
from faker import Faker

fake = Faker()

def test_get_current_user(client, test_user):
    """Test getting current user profile"""
    response = client.get("/api/users/me", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user["user"].email
    assert data["display_name"] == test_user["user"].display_name
    assert "password" not in data
    assert "hashed_password" not in data

def test_update_user_profile(client, test_user):
    """Test updating user profile"""
    update_data = {
        "display_name": fake.name(),
        "timezone": "America/New_York",
        "locale": "en-GB"
    }
    
    response = client.put("/api/users/me", headers=test_user["headers"], json=update_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["display_name"] == update_data["display_name"]
    assert data["timezone"] == update_data["timezone"]
    assert data["locale"] == update_data["locale"]

def test_update_user_password(client, test_user, db):
    """Test updating user password"""
    new_password = "newpassword123"
    update_data = {
        "password": new_password
    }
    
    # Update password
    response = client.put("/api/users/me", headers=test_user["headers"], json=update_data)
    assert response.status_code == status.HTTP_200_OK
    
    # Try logging in with new password
    login_data = {
        "username": test_user["user"].email,
        "password": new_password
    }
    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == status.HTTP_200_OK

def test_get_user_preferences(client, test_user):
    """Test getting user preferences"""
    response = client.get("/api/users/me/preferences", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "daily_word_goal" in data
    assert "writing_reminder_time" in data
    assert "theme_preferences" in data
    assert "ai_features_enabled" in data
    assert "timezone" in data
    assert "locale" in data

def test_update_user_preferences(client, test_user):
    """Test updating user preferences"""
    preferences = {
        "daily_word_goal": 1000,
        "writing_reminder_time": "09:00",
        "theme_preferences": {"dark_mode": True},
        "ai_features_enabled": False
    }
    
    response = client.put(
        "/api/users/me/preferences",
        headers=test_user["headers"],
        json=preferences
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["daily_word_goal"] == preferences["daily_word_goal"]
    assert data["writing_reminder_time"] == preferences["writing_reminder_time"]
    assert data["theme_preferences"] == preferences["theme_preferences"]
    assert data["ai_features_enabled"] == preferences["ai_features_enabled"]

def test_get_user_stats(client, test_user):
    """Test getting user statistics"""
    response = client.get("/api/users/me/stats", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_logs" in data
    assert "recent_logs" in data
    assert "total_words" in data
    assert "avg_words_per_entry" in data
    assert "writing_streak" in data
    assert "days_analyzed" in data

def test_get_user_stats_custom_days(client, test_user):
    """Test getting user statistics with custom days parameter"""
    days = 7
    response = client.get(
        f"/api/users/me/stats?days={days}",
        headers=test_user["headers"]
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["days_analyzed"] == days

def test_user_isolation(client, test_user, test_user2):
    """Test that users can't access each other's data"""
    # Try to get second user's data with first user's token
    response = client.get("/api/users/me", headers=test_user2["headers"])
    data = response.json()
    assert response.status_code == status.HTTP_200_OK
    assert data["email"] == test_user2["user"].email
    assert data["email"] != test_user["user"].email

def test_get_privacy_settings_default(client, test_user):
    """Test getting privacy settings (default should be local_only)"""
    response = client.get("/api/users/me/privacy", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_tier"] == "local_only"
    assert data["sync_enabled"] == False
    assert data["sync_enabled_at"] is None
    assert data["features_available"]["local_storage"] == True
    assert data["features_available"]["cloud_sync"] == False
    assert data["features_available"]["analytics_sync"] == False

def test_upgrade_to_analytics_sync(client, test_user):
    """Test upgrading privacy tier to analytics_sync"""
    from datetime import datetime

    tier_update = {
        "privacy_tier": "analytics_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_encoded_public_key_example"
    }

    response = client.put("/api/users/me/privacy", headers=test_user["headers"], json=tier_update)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_tier"] == "analytics_sync"
    assert data["sync_enabled"] == True
    assert data["sync_enabled_at"] is not None
    assert data["features_available"]["analytics_sync"] == True
    assert data["features_available"]["cloud_sync"] == False

def test_upgrade_to_full_sync(client, test_user):
    """Test upgrading privacy tier to full_sync"""
    from datetime import datetime

    tier_update = {
        "privacy_tier": "full_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_encoded_public_key_example"
    }

    response = client.put("/api/users/me/privacy", headers=test_user["headers"], json=tier_update)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["current_tier"] == "full_sync"
    assert data["sync_enabled"] == True
    assert data["features_available"]["cloud_sync"] == True
    assert data["features_available"]["encrypted_backup"] == True
    assert data["features_available"]["cross_device_search"] == True

def test_upgrade_requires_he_public_key(client, test_user):
    """Test that upgrading to analytics_sync or full_sync requires HE public key"""
    from datetime import datetime

    tier_update = {
        "privacy_tier": "analytics_sync",
        "consent_timestamp": datetime.utcnow().isoformat()
    }

    response = client.put("/api/users/me/privacy", headers=test_user["headers"], json=tier_update)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "HE public key required" in data["detail"]

def test_cannot_downgrade_directly(client, test_user):
    """Test that downgrading tier directly is not allowed"""
    from datetime import datetime

    upgrade = {
        "privacy_tier": "full_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_key"
    }
    client.put("/api/users/me/privacy", headers=test_user["headers"], json=upgrade)

    downgrade = {
        "privacy_tier": "analytics_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_key"
    }

    response = client.put("/api/users/me/privacy", headers=test_user["headers"], json=downgrade)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "Cannot downgrade tier directly" in data["detail"]

def test_revoke_cloud_sync(client, test_user, db):
    """Test revoking cloud sync and deleting all cloud data"""
    from datetime import datetime
    from app.models.models import EncryptedMetric, EncryptedBackup

    upgrade = {
        "privacy_tier": "full_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_key"
    }
    client.put("/api/users/me/privacy", headers=test_user["headers"], json=upgrade)

    metric = EncryptedMetric(
        user_id=test_user["user"].id,
        metric_type="word_count",
        encrypted_value=b"encrypted_data",
        timestamp=datetime.utcnow()
    )
    db.add(metric)

    backup = EncryptedBackup(
        id="backup-id",
        user_id=test_user["user"].id,
        encrypted_content=b"encrypted_content",
        content_iv="iv_string",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        device_id="test-device"
    )
    db.add(backup)
    db.commit()

    response = client.delete("/api/users/me/privacy/revoke", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["new_tier"] == "local_only"
    assert data["deleted_metrics"] == 1
    assert data["deleted_backups"] == 1

    verify = client.get("/api/users/me/privacy", headers=test_user["headers"])
    verify_data = verify.json()
    assert verify_data["current_tier"] == "local_only"
    assert verify_data["sync_enabled"] == False
    assert verify_data["sync_enabled_at"] is None

def test_progressive_tier_upgrade(client, test_user):
    """Test upgrading through all privacy tiers progressively"""
    from datetime import datetime

    get_response = client.get("/api/users/me/privacy", headers=test_user["headers"])
    assert get_response.json()["current_tier"] == "local_only"

    analytics_upgrade = {
        "privacy_tier": "analytics_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_key"
    }
    response = client.put("/api/users/me/privacy", headers=test_user["headers"], json=analytics_upgrade)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_tier"] == "analytics_sync"

    full_upgrade = {
        "privacy_tier": "full_sync",
        "consent_timestamp": datetime.utcnow().isoformat(),
        "he_public_key": "base64_key"
    }
    response = client.put("/api/users/me/privacy", headers=test_user["headers"], json=full_upgrade)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["current_tier"] == "full_sync"

    final_check = client.get("/api/users/me/privacy", headers=test_user["headers"])
    assert final_check.json()["current_tier"] == "full_sync" 