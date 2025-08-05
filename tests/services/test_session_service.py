import pytest
from datetime import datetime, timedelta
from app.services.session_service import SessionService
from app.models.models import WritingSession, Log, User
from sqlalchemy.orm import Session
import uuid

@pytest.fixture
def session_service():
    return SessionService()

@pytest.fixture
def sample_user(db: Session):
    """Create a sample user for testing"""
    user = User(
        id=str(uuid.uuid4()),  # Dynamic UUID instead of hardcoded
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",  # Unique email
        hashed_password="hashed_password",
        display_name="Test User",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    return user

@pytest.fixture
def sample_session(db: Session, sample_user):
    """Create a sample writing session for testing"""
    session = WritingSession(
        id=str(uuid.uuid4()),  # Dynamic UUID instead of hardcoded
        user_id=sample_user.id,
        started_at=datetime.utcnow(),
        session_type="freeform",
        interruption_count=0
    )
    db.add(session)
    db.commit()
    return session

def test_start_session(session_service, db: Session, sample_user):
    """Test starting a new writing session"""
    session = session_service.start_session(db, sample_user.id, "daily")
    
    assert session.id is not None
    assert session.user_id == sample_user.id
    assert session.session_type == "daily"
    assert session.started_at is not None
    assert session.ended_at is None
    assert session.interruption_count == 0

def test_start_session_with_active(session_service, db: Session, sample_user, sample_session):
    """Test starting a session when one is already active"""
    # Start new session while sample_session is active
    new_session = session_service.start_session(db, sample_user.id)
    
    # Check that old session was ended
    db.refresh(sample_session)
    assert sample_session.ended_at is not None
    
    # Check that new session was created
    assert new_session.id != sample_session.id
    assert new_session.ended_at is None

def test_end_session(session_service, db: Session, sample_session):
    """Test ending a writing session"""
    ended_session = session_service.end_session(db, sample_session.id)
    
    assert ended_session is not None
    assert ended_session.ended_at is not None
    assert ended_session.focus_score is not None
    assert 0 <= ended_session.focus_score <= 1

def test_end_nonexistent_session(session_service, db: Session):
    """Test ending a session that doesn't exist"""
    nonexistent_id = str(uuid.uuid4())  # Generate a valid but nonexistent UUID
    result = session_service.end_session(db, nonexistent_id)
    assert result is None

def test_get_active_session(session_service, db: Session, sample_user, sample_session):
    """Test getting active session"""
    active = session_service.get_active_session(db, sample_user.id)
    
    assert active is not None
    assert active.id == sample_session.id
    assert active.ended_at is None

def test_get_active_session_timeout(session_service, db: Session, sample_user, sample_session):
    """Test getting active session after timeout"""
    # Modify session start time to be beyond timeout
    sample_session.started_at = datetime.utcnow() - timedelta(minutes=31)
    db.commit()
    
    active = session_service.get_active_session(db, sample_user.id)
    
    # Should auto-end the session and return None
    assert active is None
    
    # Verify session was ended
    db.refresh(sample_session)
    assert sample_session.ended_at is not None

def test_record_interruption(session_service, db: Session, sample_session):
    """Test recording an interruption"""
    initial_count = sample_session.interruption_count
    
    updated = session_service.record_interruption(db, sample_session.id)
    
    assert updated is not None
    assert updated.interruption_count == initial_count + 1

def test_record_interruption_ended_session(session_service, db: Session, sample_session):
    """Test recording interruption for ended session"""
    # End the session
    session_service.end_session(db, sample_session.id)
    
    # Try to record interruption
    result = session_service.record_interruption(db, sample_session.id)
    assert result is None

def test_get_session_stats_empty(session_service, db: Session, sample_user):
    """Test getting stats with no sessions"""
    stats = session_service.get_session_stats(db, sample_user.id)
    
    assert stats["total_sessions"] == 0
    assert stats["total_duration"] == 0
    assert stats["avg_duration"] == 0
    assert stats["avg_focus_score"] == 0
    assert stats["completion_rate"] == 0

def test_get_session_stats(session_service, db: Session, sample_user):
    """Test getting session statistics"""
    # Create multiple sessions with different types
    sessions = [
        WritingSession(
            user_id=sample_user.id,
            started_at=datetime.utcnow() - timedelta(days=i),
            ended_at=datetime.utcnow() - timedelta(days=i, minutes=-30),
            session_type=stype,
            interruption_count=i % 2,
            focus_score=0.8
        )
        for i, stype in enumerate(["daily", "freeform", "prompted"])
    ]
    
    # Add some logs to sessions
    for session in sessions[:2]:
        log = Log(
            id=str(uuid.uuid4()),  # Use proper UUID for log ID
            user_id=sample_user.id,
            session_id=session.id,
            content="Test log content",
            created_at=session.started_at,
            updated_at=session.started_at
        )
        session.logs.append(log)
    
    for session in sessions:
        db.add(session)
    db.commit()
    
    # Get stats
    stats = session_service.get_session_stats(db, sample_user.id, days=7)
    
    assert stats["total_sessions"] == 3
    assert stats["total_duration"] > 0
    assert stats["avg_duration"] > 0
    assert stats["avg_focus_score"] == pytest.approx(0.8)
    assert len(stats["session_types"]) == 3
    assert stats["completion_rate"] == 2/3  # 2 out of 3 sessions have logs

def test_focus_score_calculation(session_service, db: Session, sample_user):
    """Test focus score calculation with different scenarios"""
    def create_session(duration_mins: int, interruptions: int) -> WritingSession:
        session = WritingSession(
            user_id=sample_user.id,
            started_at=datetime.utcnow() - timedelta(minutes=duration_mins),
            ended_at=datetime.utcnow(),
            session_type="freeform",
            interruption_count=interruptions
        )
        db.add(session)
        db.commit()
        return session
    
    # Short session with interruptions
    short_session = create_session(4, 2)
    short_score = session_service._calculate_focus_score(short_session)
    
    # Medium session with no interruptions
    medium_session = create_session(10, 0)
    medium_score = session_service._calculate_focus_score(medium_session)
    
    # Long focused session
    long_session = create_session(35, 0)
    long_score = session_service._calculate_focus_score(long_session)
    
    # Long interrupted session
    interrupted_session = create_session(35, 5)
    interrupted_score = session_service._calculate_focus_score(interrupted_session)
    
    # Verify score relationships
    assert short_score < medium_score  # Short duration penalty
    assert medium_score < long_score  # Long duration bonus
    assert interrupted_score < long_score  # Interruption penalty
    assert 0 <= short_score <= 1
    assert 0 <= medium_score <= 1
    assert 0 <= long_score <= 1
    assert 0 <= interrupted_score <= 1 