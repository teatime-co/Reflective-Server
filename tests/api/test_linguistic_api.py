import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app.main import app
from app.models.models import Log, LinguisticMetrics
from unittest.mock import patch
import uuid

client = TestClient(app)

@pytest.fixture
def mock_embeddings():
    """Mock embedding response from Ollama"""
    return [0.1] * 1024  # Typical embedding dimension

@pytest.fixture
def mock_ollama_api(mock_embeddings):
    """Mock Ollama API responses"""
    with patch('requests.post') as mock_post:
        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": mock_embeddings}
        yield mock_post

@pytest.fixture
def sample_log(db, test_user):
    """Create a sample log for testing"""
    log = Log(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        content="I had a great day today! The project at work is going well, and I'm feeling very optimistic about our progress.",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    return log

@pytest.fixture
def sample_metrics(db, sample_log):
    """Create sample linguistic metrics for testing"""
    metrics = LinguisticMetrics(
        id=uuid.uuid4(),
        log_id=sample_log.id,
        vocabulary_diversity_score=0.8,
        sentiment_score=0.6,
        complexity_score=0.7,
        readability_level=85.0,
        emotion_scores={
            "emotions": {
                "joy": 0.8,
                "sadness": 0.1,
                "anger": 0.1,
                "fear": 0.1,
                "surprise": 0.2
            },
            "subjectivity": 0.6
        },
        writing_style_metrics={
            "sentence_types": {"declarative": 0.8},
            "style_similarities": {
                "formal": 0.3,
                "casual": 0.7,
                "technical": 0.2,
                "narrative": 0.5,
                "persuasive": 0.4
            },
            "formality_indicators": {
                "academic_words": 0.3,
                "personal_pronouns": 0.2
            }
        },
        processed_at=datetime.utcnow()
    )
    db.add(metrics)
    db.commit()
    return metrics

def test_analyze_text(test_user, client, mock_ollama_api):
    """Test text analysis endpoint"""
    text = "This is a test sentence. It contains multiple words and some emotion! I am feeling happy."
    
    response = client.post(
        "/api/linguistic/analyze",
        headers=test_user["headers"],
        json={"text": text}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check all required metrics are present
    assert "vocabulary_diversity_score" in data
    assert "sentiment_score" in data
    assert "complexity_score" in data
    assert "readability_level" in data
    assert "emotion_scores" in data
    assert "writing_style_metrics" in data
    
    # Check metric ranges
    assert 0 <= data["vocabulary_diversity_score"] <= 1
    assert -1 <= data["sentiment_score"] <= 1
    assert data["complexity_score"] >= 0
    assert 0 <= data["readability_level"] <= 100
    
    # Check embedding-based metrics
    emotions = data["emotion_scores"]["emotions"]
    for emotion in ["joy", "sadness", "anger", "fear", "surprise"]:
        assert emotion in emotions
        assert 0 <= emotions[emotion] <= 1
        
    style = data["writing_style_metrics"]
    assert "style_similarities" in style
    for style_type in ["formal", "casual", "technical", "narrative", "persuasive"]:
        assert style_type in style["style_similarities"]
        assert 0 <= style["style_similarities"][style_type] <= 1

def test_analyze_text_empty(test_user, client, mock_ollama_api):
    """Test analysis of empty text"""
    response = client.post(
        "/api/linguistic/analyze",
        headers=test_user["headers"],
        json={"text": ""}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["vocabulary_diversity_score"] == 0
    assert data["complexity_score"] == 0
    assert data["readability_level"] == 0
    
    # Check empty text emotions
    emotions = data["emotion_scores"]["emotions"]
    for emotion in ["joy", "sadness", "anger", "fear", "surprise"]:
        assert emotions[emotion] == 0

def test_process_log(test_user, client, sample_log, mock_ollama_api):
    """Test processing a log entry"""
    response = client.post(
        f"/api/linguistic/process/{sample_log.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["log_id"] == str(sample_log.id)
    
    # Check all metrics are present and valid
    assert "vocabulary_diversity_score" in data
    assert "sentiment_score" in data
    assert "emotion_scores" in data
    assert "writing_style_metrics" in data
    assert "processed_at" in data
    
    # Check embedding-based metrics
    assert "emotions" in data["emotion_scores"]
    assert "style_similarities" in data["writing_style_metrics"]

def test_process_nonexistent_log(test_user, client):
    """Test processing a nonexistent log"""
    nonexistent_id = str(uuid.uuid4())  # Generate valid UUID
    response = client.post(
        f"/api/linguistic/process/{nonexistent_id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 404

def test_process_unauthorized_log(test_user, test_user2, client, db):
    """Test processing an unauthorized log"""
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
        f"/api/linguistic/process/{log.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 403

def test_get_metrics(test_user, client, sample_log, sample_metrics):
    """Test getting metrics for a log"""
    response = client.get(
        f"/api/linguistic/metrics/{sample_log.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["log_id"] == str(sample_log.id)
    assert "emotion_scores" in data
    assert "writing_style_metrics" in data

def test_get_metrics_no_metrics(test_user, client, sample_log):
    """Test getting metrics when none exist"""
    response = client.get(
        f"/api/linguistic/metrics/{sample_log.id}",
        headers=test_user["headers"]
    )
    
    assert response.status_code == 404 