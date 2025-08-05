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