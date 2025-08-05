import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from app.main import app
from app.models.models import WritingSession, Log
import uuid

# Remove local client fixture and use the one from conftest.py

@pytest.fixture
def active_session(db, test_user):
    """Create an active session for testing"""
    session = WritingSession(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        started_at=datetime.utcnow(),
        session_type="freeform",
        interruption_count=0
    )
    db.add(session)
    db.commit()
    return session

def test_start_session(client, test_user):
    """Test starting a new session"""
    response = client.post(
        "/api/sessions/start",
        headers=test_user["headers"],
        json={"session_type": "daily"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["session_type"] == "daily"
    assert data["ended_at"] is None
    assert data["interruption_count"] == 0

def test_start_session_with_active(client, test_user, active_session, db):
    """Test starting a session when one is already active"""
    response = client.post(
        "/api/sessions/start",
        headers=test_user["headers"],
        json={"session_type": "prompted"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that new session was created
    assert data["id"] != str(active_session.id)
    
    # Check that old session was ended
    db.refresh(active_session)
    assert active_session.ended_at is not None

def test_end_session(client, test_user, active_session):
    """Test ending a session"""
    response = client.post(
        f"/api/sessions/end/{active_session.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(active_session.id)
    assert data["ended_at"] is not None
    assert data["focus_score"] is not None

def test_end_nonexistent_session(client, test_user):
    """Test ending a nonexistent session"""
    nonexistent_uuid = str(uuid.uuid4())  # Generate a random UUID that doesn't exist
    response = client.post(
        f"/api/sessions/end/{nonexistent_uuid}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 404

def test_get_active_session(client, test_user, active_session):
    """Test getting active session"""
    response = client.get(
        "/api/sessions/active",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(active_session.id)
    assert data["ended_at"] is None

def test_get_active_session_none(client, test_user):
    """Test getting active session when none exists"""
    response = client.get(
        "/api/sessions/active",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    assert response.json() is None

def test_record_interruption(client, test_user, active_session):
    """Test recording an interruption"""
    response = client.post(
        f"/api/sessions/interrupt/{active_session.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["interruption_count"] == 1

def test_record_interruption_ended_session(client, test_user, active_session, db):
    """Test recording interruption for ended session"""
    # End the session
    active_session.ended_at = datetime.utcnow()
    db.commit()
    
    response = client.post(
        f"/api/sessions/interrupt/{active_session.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 404

def test_get_session_stats(client, test_user, db):
    """Test getting session statistics"""
    # Create some test sessions
    sessions = []
    for i, stype in enumerate(["daily", "freeform", "prompted"]):
        session = WritingSession(
            user_id=test_user["user"].id,
            started_at=datetime.utcnow() - timedelta(days=i),
            ended_at=datetime.utcnow() - timedelta(days=i, minutes=-30),
            session_type=stype,
            interruption_count=i % 2,
            focus_score=0.8
        )
        sessions.append(session)
        db.add(session)
    db.commit()
    
    # Add some logs to sessions
    for session in sessions[:2]:
        log = Log(
            id=str(uuid.uuid4()),
            user_id=test_user["user"].id,
            session_id=session.id,
            content="Test log content",
            created_at=session.started_at,
            updated_at=session.started_at,
            word_count=3,
            processing_status="processed"
        )
        session.logs.append(log)
    
    for session in sessions:
        db.add(session)
    db.commit()
    
    response = client.get(
        "/api/sessions/stats?days=7",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 3
    assert abs(data["avg_focus_score"] - 0.8) < 0.0001  # Use approximate comparison for floats
    assert len(data["session_types"]) == 3

def test_get_session_stats_empty(client, test_user):
    """Test getting stats with no sessions"""
    response = client.get(
        "/api/sessions/stats",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 0
    assert data["total_duration"] == 0
    assert data["avg_duration"] == 0
    assert data["avg_focus_score"] == 0
    assert data["completion_rate"] == 0

def test_get_session_stats_different_users(client, test_user, test_user2, db):
    """Test that session stats are user-specific"""
    # Create sessions for both users
    for user in [test_user, test_user2]:
        session = WritingSession(
            user_id=user["user"].id,
            started_at=datetime.utcnow(),
            ended_at=datetime.utcnow() + timedelta(minutes=30),
            session_type="freeform",
            focus_score=0.8
        )
        db.add(session)
    db.commit()
    
    # Get stats for first user
    response = client.get(
        "/api/sessions/stats",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 1  # Should only see their own session 