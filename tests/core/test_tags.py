import pytest
from fastapi import status
import uuid
from datetime import datetime, timedelta
from app.models.models import Tag

@pytest.fixture
def test_tag(db, test_user):
    """Create a test tag directly in the database"""
    tag = Tag(
        user_id=test_user["user"].id,
        name=f"test_tag_{uuid.uuid4().hex[:8]}",
        color="#FF0000",
        created_at=datetime.utcnow(),
        last_used_at=datetime.utcnow()
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)

    return {
        "id": tag.id,
        "name": tag.name,
        "color": tag.color,
        "created_at": tag.created_at
    }

def test_get_tags(client, test_user, test_tag):
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
        "name": f"test_tag_{uuid.uuid4().hex[:8]}",
        "color": "#FF0000"
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
    """Test creating a tag with existing name for the same user"""
    tag_data = {
        "name": test_tag["name"],
        "color": "#00FF00"
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
