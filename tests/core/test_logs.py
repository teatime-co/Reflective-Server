import pytest
from fastapi import status
from faker import Faker
import uuid

fake = Faker()

@pytest.fixture
def test_log(client, test_user, db):
    """Create a test log"""
    log_data = {
        "id": str(uuid.uuid4()),
        "content": fake.text(),
        "tags": ["test", "sample"]
    }
    
    response = client.post(
        "/api/logs/",
        headers=test_user["headers"],
        json=log_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()

def test_create_log(client, test_user):
    """Test creating a new log"""
    log_data = {
        "id": str(uuid.uuid4()),
        "content": fake.text(),
        "tags": ["test", "sample"]
    }
    
    response = client.post(
        "/api/logs/",
        headers=test_user["headers"],
        json=log_data
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["content"] == log_data["content"]
    assert data["user_id"] == str(test_user["user"].id)
    assert len(data["tags"]) == len(log_data["tags"])

def test_get_logs(client, test_user, test_log):
    """Test getting user's logs"""
    response = client.get("/api/logs/", headers=test_user["headers"])
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
    assert data[0]["user_id"] == str(test_user["user"].id)

def test_get_logs_with_tag(client, test_user, test_log):
    """Test getting logs filtered by tag"""
    tag = test_log["tags"][0]["name"]

    response = client.get(
        f"/api/logs/?tag={tag}",
        headers=test_user["headers"]
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) > 0
    assert any(t["name"] == tag for t in data[0]["tags"])

def test_get_specific_log(client, test_user, test_log):
    """Test getting a specific log"""
    response = client.get(
        f"/api/logs/{test_log['id']}",
        headers=test_user["headers"]
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == test_log["id"]
    assert data["content"] == test_log["content"]

def test_update_log(client, test_user, test_log):
    """Test updating a log"""
    update_data = {
        "content": fake.text()
    }
    
    response = client.put(
        f"/api/logs/{test_log['id']}",
        headers=test_user["headers"],
        json=update_data
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["content"] == update_data["content"]
    assert data["id"] == test_log["id"]

def test_delete_log(client, test_user, test_log):
    """Test deleting a log"""
    response = client.delete(
        f"/api/logs/{test_log['id']}",
        headers=test_user["headers"]
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify log is deleted
    response = client.get(
        f"/api/logs/{test_log['id']}",
        headers=test_user["headers"]
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_log_isolation(client, test_user, test_user2, test_log):
    """Test that users can't access each other's logs"""
    # Try to get first user's log with second user's token
    response = client.get(
        f"/api/logs/{test_log['id']}",
        headers=test_user2["headers"]
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_search_logs(client, test_user, test_log):
    """Test semantic search on logs"""
    response = client.post(
        "/api/search",
        headers=test_user["headers"],
        params={"query": "test", "top_k": 5}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "relevance_score" in data[0]
        assert "snippet_text" in data[0]
        assert data[0]["user_id"] == str(test_user["user"].id)

def test_search_similar_queries(client, test_user):
    """Test getting similar queries"""
    response = client.get(
        "/api/search/similar",
        headers=test_user["headers"],
        params={"query": "test", "limit": 5}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)

def test_search_suggestions(client, test_user):
    """Test getting query suggestions"""
    response = client.get(
        "/api/search/suggest",
        headers=test_user["headers"],
        params={"partial_query": "te", "limit": 5}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list) 