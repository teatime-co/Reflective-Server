import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid
from app.main import app
from app.models.models import Theme, Log

client = TestClient(app)

@pytest.fixture
def sample_themes(db, test_user):
    """Create sample themes for testing"""
    themes = [
        Theme(
            id=uuid.uuid4(),
            user_id=test_user["user"].id,
            name="personal growth",
            description="Entries about self-improvement and development",
            created_at=datetime.utcnow()
        ),
        Theme(
            id=uuid.uuid4(),
            user_id=test_user["user"].id,
            name="work",
            description="Professional life and career",
            created_at=datetime.utcnow()
        ),
        Theme(
            id=uuid.uuid4(),
            user_id=test_user["user"].id,
            name="photography",
            description="Capturing moments and visual storytelling",
            created_at=datetime.utcnow()
        ),
        Theme(
            id=uuid.uuid4(),
            user_id=test_user["user"].id,
            name="landscape photography",
            description="Nature scenes and outdoor photography adventures",
            created_at=datetime.utcnow()
        ),
        Theme(
            id=uuid.uuid4(),
            user_id=test_user["user"].id,
            name="street photography",
            description="Urban life and candid moments in the city",
            created_at=datetime.utcnow()
        )
    ]
    for theme in themes:
        db.add(theme)
    db.commit()
    return themes

@pytest.fixture
def sample_log(db, test_user):
    """Create a sample log for testing"""
    log = Log(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        content="I'm working on improving my skills and advancing my career.",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    return log

def test_get_themes(test_user, client, sample_themes):
    """Test getting all themes"""
    response = client.get(
        "/api/themes",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    assert data[0]["name"] == "personal growth"
    assert data[1]["name"] == "work"
    assert all(theme["user_id"] == str(test_user["user"].id) for theme in data)

def test_get_theme(test_user, client, sample_themes):
    """Test getting a specific theme"""
    theme_id = str(sample_themes[0].id)
    response = client.get(
        f"/api/themes/{theme_id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == theme_id
    assert data["name"] == "personal growth"
    assert data["user_id"] == str(test_user["user"].id)

def test_get_nonexistent_theme(test_user, client):
    """Test getting a theme that doesn't exist"""
    response = client.get(
        f"/api/themes/{uuid.uuid4()}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 404

def test_detect_themes(test_user, client, sample_themes, sample_log):
    """Test theme detection for a log"""
    print("\n=== Debug: test_detect_themes ===")
    print(f"Log content: {sample_log.content}")
    print(f"Available themes:")
    for theme in sample_themes:
        print(f"  - {theme.name}: {theme.description}")

    response = client.post(
        f"/api/themes/detect/{sample_log.id}",
        headers=test_user["headers"]
    )

    print(f"\nResponse status: {response.status_code}")
    data = response.json()
    print(f"Response data: {data}")

    assert response.status_code == 200
    assert len(data) > 0, "No themes were detected"

    theme_names = [match["theme"]["name"] for match in data]
    print(f"\nDetected theme names: {theme_names}")

    assert "work" in theme_names, "'work' theme not detected"
    assert "personal growth" in theme_names, "'personal growth' theme not detected"

    print("\nConfidence scores:")
    for match in data:
        print(f"  {match['theme']['name']}: {match['confidence_score']}")
        assert 0 <= match["confidence_score"] <= 1
        assert match["theme"]["user_id"] == str(test_user["user"].id)

def test_detect_themes_unauthorized(test_user, test_user2, client, sample_themes, db):
    """Test theme detection for unauthorized log"""
    # Create log for different user
    log = Log(
        id=uuid.uuid4(),
        user_id=test_user2["user"].id,
        content="Test content",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    response = client.post(
        f"/api/themes/detect/{log.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 403

def test_suggest_themes(test_user, client):
    """Test theme suggestion generation"""
    text = "I've been working on improving my photography skills. The composition techniques are challenging but rewarding."

    response = client.post(
        "/api/themes/suggest",
        headers=test_user["headers"],
        params={
            "text": text,
            "max_suggestions": 3
        }
    )

    assert response.status_code == 200
    data = response.json()
    suggestions = data["suggested_themes"]
    assert len(suggestions) <= 3
    assert len(suggestions) > 0

    suggested_phrases = [phrase.lower() for phrase in suggestions]
    assert any("photography" in phrase for phrase in suggested_phrases) or any("photographic" in phrase for phrase in suggested_phrases)

def test_suggest_themes_empty(test_user, client):
    """Test theme suggestions with empty text"""
    response = client.post(
        "/api/themes/suggest",
        headers=test_user["headers"],
        params={
            "text": "",
            "max_suggestions": 5
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["suggested_themes"]) == 0 