import pytest
from fastapi import status
import uuid
from datetime import datetime, timedelta

@pytest.fixture
def test_tag(client, test_user, test_log):
    """Get a test tag from the test log"""
    return test_log["tags"][0]

def test_get_tags(client, test_user, test_log):
    """Test getting user's tags"""
    response = client.get("/api/tags", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
    assert isinstance(data, list)
    assert all(isinstance(tag["name"], str) for tag in data)

def test_create_tag(client, test_user):
    """Test creating a new tag"""
    tag_data = {
        "id": str(uuid.uuid4()),
        "name": f"test_tag_{uuid.uuid4().hex[:8]}",
        "color": "#FF0000",
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = client.post(
        "/api/tags",
        headers=test_user["headers"],
        json=tag_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == tag_data["name"]
    assert data["color"] == tag_data["color"]

def test_create_duplicate_tag(client, test_user, test_tag):
    """Test creating a tag with existing name"""
    tag_data = {
        "id": str(uuid.uuid4()),
        "name": test_tag["name"],
        "color": "#00FF00",
        "created_at": datetime.utcnow().isoformat()
    }
    
    response = client.post(
        "/api/tags",
        headers=test_user["headers"],
        json=tag_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == test_tag["name"]
    # Should return existing tag
    assert uuid.UUID(data["id"]) == test_tag["id"]

def test_cleanup_stale_tags(client, test_user, test_user2, db):
    """Test cleaning up stale tags"""
    # Create a log with a unique tag for test_user
    log_data = {
        "id": str(uuid.uuid4()),
        "content": "Test content",
        "tags": [f"unique_tag_{uuid.uuid4().hex[:8]}"]
    }
    response = client.post(
        "/api/logs/",
        headers=test_user["headers"],
        json=log_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    
    # Create a log with a shared tag for both users
    shared_tag = f"shared_tag_{uuid.uuid4().hex[:8]}"
    for user in [test_user, test_user2]:
        log_data = {
            "id": str(uuid.uuid4()),
            "content": "Test content",
            "tags": [shared_tag]
        }
        response = client.post(
            "/api/logs/",
            headers=user["headers"],
            json=log_data
        )
        assert response.status_code == status.HTTP_201_CREATED
    
    # Run cleanup for test_user
    response = client.delete(
        "/api/tags/cleanup",
        headers=test_user["headers"],
        params={"days": 1}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "deleted_count" in data
    
    # Verify shared tag still exists
    response = client.get("/api/tags", headers=test_user2["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert any(tag["name"] == shared_tag for tag in data)

def test_tag_isolation(client, test_user, test_user2):
    """Test that users only see their own tags"""
    # Create a unique tag for test_user2
    unique_tag = f"unique_tag_{uuid.uuid4().hex[:8]}"
    log_data = {
        "id": str(uuid.uuid4()),
        "content": "Test content",
        "tags": [unique_tag]
    }
    response = client.post(
        "/api/logs/",
        headers=test_user2["headers"],
        json=log_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    
    # Verify test_user cannot see test_user2's unique tag
    response = client.get("/api/tags", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert not any(tag["name"] == unique_tag for tag in data) 