import pytest
from datetime import datetime
from app.services.theme_service import ThemeService
from app.models.models import Theme, Log, log_theme_association, User
from sqlalchemy.orm import Session
from typing import List, Dict

@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(
        id="550e8400-e29b-41d4-a716-446655440001",
        email="test@example.com",
        hashed_password="test_hash",
        display_name="Test User"
    )
    db.add(user)
    db.commit()
    return user

@pytest.fixture
def theme_service():
    return ThemeService()

@pytest.fixture
def sample_themes(db: Session, test_user):
    """Create sample themes for testing"""
    themes = [
        Theme(name="personal growth", 
              description="Entries about self-improvement, learning, and development",
              user_id=test_user.id),
        Theme(name="relationships", 
              description="Content about interpersonal connections, family, and friends",
              user_id=test_user.id),
        Theme(name="work", 
              description="Professional life, career development, and workplace experiences",
              user_id=test_user.id),
        Theme(name="health", 
              description="Physical and mental well-being, exercise, and lifestyle",
              user_id=test_user.id)
    ]
    for theme in themes:
        db.add(theme)
    db.commit()
    return themes

@pytest.fixture
def sample_log(db: Session, test_user):
    """Create a sample log for testing"""
    log = Log(
        id="550e8400-e29b-41d4-a716-446655440000",
        user_id=test_user.id,
        content="Today I had a great workout at the gym and felt energized. I'm making progress on my fitness goals while balancing work responsibilities. My friend Sarah noticed my improved mood and energy levels.",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    return log

def test_detect_themes_basic(theme_service, sample_themes):
    """Test basic theme detection"""
    text = "I'm working hard on my career development and learning new skills."
    
    matches = theme_service.detect_themes(text, sample_themes)
    
    assert len(matches) > 0
    # Should match work and personal growth themes
    theme_names = [match["theme"].name for match in matches]
    assert "work" in theme_names
    assert "personal growth" in theme_names

def test_detect_themes_empty(theme_service, sample_themes):
    """Test theme detection with empty text"""
    matches = theme_service.detect_themes("", sample_themes)
    assert len(matches) == 0

def test_detect_themes_confidence(theme_service, sample_themes):
    """Test confidence scores in theme detection"""
    text = "I had a great workout today and my energy levels are improving."
    
    matches = theme_service.detect_themes(text, sample_themes, confidence_threshold=0.1)
    
    # Should match health theme with good confidence
    health_matches = [m for m in matches if m["theme"].name == "health"]
    assert len(health_matches) == 1
    assert health_matches[0]["confidence_score"] > 0.1

def test_process_log(theme_service, db: Session, sample_log, sample_themes):
    """Test processing a complete log entry"""
    # Process the log
    matches = theme_service.process_log(db, sample_log)
    
    # Check that themes were detected
    assert len(matches) > 0
    
    # Check that associations were created
    db.refresh(sample_log)
    assert len(sample_log.themes) > 0
    
    # Should match health and work themes
    theme_names = [theme.name for theme in sample_log.themes]
    assert "health" in theme_names
    assert "work" in theme_names

def test_process_log_empty_content(theme_service, db: Session, test_user):
    """Test processing a log with empty content"""
    log = Log(
        id="550e8400-e29b-41d4-a716-446655440002",
        user_id=test_user.id,  # Use the test_user fixture
        content="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    matches = theme_service.process_log(db, log)
    assert len(matches) == 0

def test_create_theme(theme_service, db: Session, test_user):
    """Test theme creation"""
    name = "creativity"
    description = "Artistic expression and creative processes"
    
    theme = theme_service.create_theme(db, test_user.id, name, description)  # Fix parameter order
    
    assert theme.id is not None
    assert theme.name == name
    assert theme.description == description
    assert theme.user_id == test_user.id
    
    # Check it was saved to database
    db_theme = db.query(Theme).filter_by(name=name, user_id=test_user.id).first()
    assert db_theme is not None
    assert db_theme.id == theme.id

def test_update_theme_associations(theme_service, db: Session, sample_log, sample_themes):
    """Test updating theme associations"""
    # Initial processing
    initial_matches = theme_service.process_log(db, sample_log)
    
    # Store initial theme IDs and their associations
    initial_theme_ids = {match["theme"].id for match in initial_matches}
    
    # Verify initial associations were created properly
    db.refresh(sample_log)
    for match in initial_matches:
        assoc = db.query(log_theme_association).filter_by(
            log_id=sample_log.id,
            theme_id=match["theme"].id
        ).first()
        assert assoc is not None
        assert abs(assoc.confidence_score - match["confidence_score"]) < 0.0001
    
    # Update log content to match different themes
    sample_log.content = "Focusing on learning new programming languages and improving my technical skills."
    db.commit()
    
    # Process again
    new_matches = theme_service.process_log(db, sample_log)
    new_theme_ids = {match["theme"].id for match in new_matches}
    
    # Verify new associations
    db.refresh(sample_log)
    
    # Verify old associations were removed
    for old_theme_id in initial_theme_ids:
        old_assoc = db.query(log_theme_association).filter_by(
            log_id=sample_log.id,
            theme_id=old_theme_id
        ).first()
        # If this theme isn't in new matches, its association should be gone
        if old_theme_id not in new_theme_ids:
            assert old_assoc is None, f"Old theme association {old_theme_id} should have been removed"
    
    # Verify new associations were created with correct confidence scores
    for match in new_matches:
        new_assoc = db.query(log_theme_association).filter_by(
            log_id=sample_log.id,
            theme_id=match["theme"].id
        ).first()
        assert new_assoc is not None, f"New theme association {match['theme'].id} should exist"
        assert abs(new_assoc.confidence_score - match["confidence_score"]) < 0.0001
    
    # Verify total association count matches new_matches
    total_assocs = db.query(log_theme_association).filter_by(log_id=sample_log.id).count()
    assert total_assocs == len(new_matches)

def test_get_theme_suggestions(theme_service, db: Session):
    """Test theme suggestion generation"""
    text = "I've been working on improving my photography skills. The composition techniques are challenging but rewarding. My portfolio is growing steadily."
    user_id = "550e8400-e29b-41d4-a716-446655440001"  # Using same test user ID
    
    suggestions = theme_service.get_theme_suggestions(db, text, user_id)
    
    assert len(suggestions) > 0
    # Should suggest photography-related themes
    suggested_phrases = [phrase.lower() for phrase in suggestions]
    assert any("photography" in phrase for phrase in suggested_phrases) or any("photographic" in phrase for phrase in suggested_phrases)

def test_theme_suggestion_relevance(theme_service, db: Session):
    """Test relevance of theme suggestions"""
    text = "The project deadline is approaching. Team collaboration has been excellent, and we're making good progress on the deliverables."
    user_id = "550e8400-e29b-41d4-a716-446655440001"  # Using same test user ID
    
    suggestions = theme_service.get_theme_suggestions(db, text, user_id, max_suggestions=3)
    
    # Check suggestion count
    assert len(suggestions) <= 3
    
    # Check relevance of suggestions
    relevant_terms = ["project", "team", "collaboration", "deliverables"]
    assert any(term in " ".join(suggestions).lower() for term in relevant_terms) 