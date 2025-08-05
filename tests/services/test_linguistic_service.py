import pytest
from datetime import datetime
from app.services.linguistic_service import LinguisticService
from app.models.models import Log, LinguisticMetrics, User
from sqlalchemy.orm import Session
import requests
from unittest.mock import patch, MagicMock

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
def linguistic_service():
    # Check if Ollama is available
    try:
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "snowflake-arctic-embed2",
                "prompt": "test"
            }
        )
        if response.status_code != 200:
            pytest.skip("Ollama API is not responding correctly")
    except requests.exceptions.RequestException:
        pytest.skip("Ollama API is not available")
        
    return LinguisticService()

@pytest.fixture
def sample_log(db: Session, test_user):
    """Create a sample log for testing"""
    log = Log(
        id="550e8400-e29b-41d4-a716-446655440000",
        user_id=test_user.id,
        content="This is a test log entry. It contains multiple sentences! How well will it be analyzed? I am feeling happy and excited about this test.",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    return log

def test_analyze_text_basic(linguistic_service):
    """Test basic text analysis functionality"""
    text = "This is a simple test sentence. It should work well!"
    
    metrics = linguistic_service.analyze_text(text)
    
    # Check all required metrics are present
    assert "vocabulary_diversity_score" in metrics
    assert "sentiment_score" in metrics
    assert "complexity_score" in metrics
    assert "readability_level" in metrics
    assert "emotion_scores" in metrics
    assert "writing_style_metrics" in metrics
    
    # Check metric values are in expected ranges
    assert 0 <= metrics["vocabulary_diversity_score"] <= 1
    assert -1 <= metrics["sentiment_score"] <= 1
    assert metrics["complexity_score"] >= 0
    assert 0 <= metrics["readability_level"] <= 100
    
    # Check new embedding-based metrics
    assert "emotions" in metrics["emotion_scores"]
    assert "style_similarities" in metrics["writing_style_metrics"]
    
    # Verify emotion scores
    emotions = metrics["emotion_scores"]["emotions"]
    for emotion in ["joy", "sadness", "anger", "fear", "surprise"]:
        assert emotion in emotions
        assert 0 <= emotions[emotion] <= 1
        
    # Verify style similarities
    style_sims = metrics["writing_style_metrics"]["style_similarities"]
    for style in ["formal", "casual", "technical", "narrative", "persuasive"]:
        assert style in style_sims
        assert 0 <= style_sims[style] <= 1

def test_analyze_text_empty(linguistic_service):
    """Test analysis of empty text"""
    metrics = linguistic_service.analyze_text("")
    
    assert metrics["vocabulary_diversity_score"] == 0
    assert metrics["complexity_score"] == 0
    assert metrics["readability_level"] == 0
    
    # Check empty text emotion scores
    emotions = metrics["emotion_scores"]["emotions"]
    for emotion in ["joy", "sadness", "anger", "fear", "surprise"]:
        assert emotions[emotion] == 0

def test_analyze_text_emotions(linguistic_service):
    """Test emotion analysis"""
    print("\n[TEST] Starting emotion analysis test...")
    text = "I am feeling very happy and excited! This is wonderful news."
    
    metrics = linguistic_service.analyze_text(text)
    emotions = metrics["emotion_scores"]["emotions"]
    
    print(f"\n[TEST] Input text: {text}")
    print("\n[TEST] Emotion scores:")
    for emotion, score in emotions.items():
        print(f"[TEST] - {emotion}: {score:.3f}")
    
    # Calculate average score (0.2 for 5 emotions)
    avg_score = 1.0 / len(emotions)
    min_dominant_ratio = 1.5  # Dominant emotion should be at least 1.5x the average
    
    print(f"\n[TEST] Checking assertions...")
    # Joy should be significantly above average (at least 1.5x the average of 0.2)
    assert emotions["joy"] > (avg_score * min_dominant_ratio), \
        f"Joy score ({emotions['joy']:.3f}) should be at least {min_dominant_ratio}x the average ({avg_score:.3f})"
    print(f"[TEST] ✓ Joy score ({emotions['joy']:.3f}) is significantly above average ({avg_score:.3f})")
    
    assert "subjectivity" in metrics["emotion_scores"]
    print(f"[TEST] ✓ Subjectivity present in metrics (value: {metrics['emotion_scores']['subjectivity']:.3f})")
    
    # Test emotion score relationships
    other_emotions = [e for e in emotions.keys() if e != "joy"]
    for other in other_emotions:
        assert emotions["joy"] > emotions[other], f"Joy should be higher than {other}"
        print(f"[TEST] ✓ Joy ({emotions['joy']:.3f}) > {other} ({emotions[other]:.3f})")
    
    # Verify scores are normalized
    total_score = sum(emotions.values())
    assert 0.99 <= total_score <= 1.01, f"Emotion scores should sum to 1.0 (got {total_score:.3f})"
    print(f"[TEST] ✓ Scores are properly normalized (sum = {total_score:.3f})")
    
    print("\n[TEST] All assertions passed! ✓")

def test_analyze_text_writing_style(linguistic_service):
    """Test writing style analysis"""
    text = "This is a test. Is it working? Wow, it is!"
    
    metrics = linguistic_service.analyze_text(text)
    style = metrics["writing_style_metrics"]
    
    # Test traditional metrics
    assert "sentence_types" in style
    assert style["sentence_types"]["declarative"] > 0
    assert style["sentence_types"]["interrogative"] > 0
    assert style["sentence_types"]["exclamatory"] > 0
    
    # Test embedding-based style metrics
    assert "style_similarities" in style
    for style_type in ["formal", "casual", "technical", "narrative", "persuasive"]:
        assert style_type in style["style_similarities"]
        assert 0 <= style["style_similarities"][style_type] <= 1

def test_semantic_complexity(linguistic_service):
    """Test semantic complexity calculation"""
    simple_text = "The cat sat on the mat. It was happy."
    complex_text = "The intricate interplay between quantum mechanical phenomena and macroscopic observations presents a fascinating paradox that challenges our fundamental understanding of reality."
    
    simple_metrics = linguistic_service.analyze_text(simple_text)
    complex_metrics = linguistic_service.analyze_text(complex_text)
    
    # Complex text should have higher complexity score
    assert complex_metrics["complexity_score"] > simple_metrics["complexity_score"]
    assert 0 <= simple_metrics["complexity_score"] <= 1  # Scores should be normalized
    assert 0 <= complex_metrics["complexity_score"] <= 1

def test_ollama_api_failure(linguistic_service):
    """Test graceful handling of Ollama API failures"""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.RequestException("API Error")
        
        # Should still work but fall back to basic analysis
        metrics = linguistic_service.analyze_text("Test text")
        
        assert "emotions" in metrics["emotion_scores"]
        assert "style_similarities" not in metrics["writing_style_metrics"]

def test_process_log(linguistic_service, db: Session, sample_log):
    """Test processing a complete log entry"""
    # Process the log
    metrics = linguistic_service.process_log(db, sample_log)
    
    # Check that metrics were created
    assert metrics is not None
    assert isinstance(metrics, LinguisticMetrics)
    assert metrics.log_id == sample_log.id
    
    # Check that metrics were saved to database
    db.refresh(sample_log)
    assert sample_log.linguistic_metrics is not None
    assert sample_log.linguistic_metrics.id == metrics.id

def test_process_log_empty_content(linguistic_service, db: Session, test_user):
    """Test processing a log with empty content"""
    log = Log(
        id="550e8400-e29b-41d4-a716-446655440002",
        user_id=test_user.id,
        content="",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    metrics = linguistic_service.process_log(db, log)
    assert metrics is None

def test_process_log_update_existing(linguistic_service, db: Session, sample_log):
    """Test updating existing metrics"""
    # Create initial metrics
    initial_metrics = linguistic_service.process_log(db, sample_log)
    initial_id = initial_metrics.id
    initial_sentiment = initial_metrics.sentiment_score
    
    # Update log content with text that should have different sentiment
    sample_log.content = "This is absolutely wonderful! I'm so happy and excited about everything!"
    db.commit()
    
    # Process again
    updated_metrics = linguistic_service.process_log(db, sample_log)
    
    # Check that we updated existing record
    assert updated_metrics.id == initial_id  # Same record
    assert updated_metrics.sentiment_score != initial_sentiment  # Metrics actually updated
    assert updated_metrics.processed_at is not None  # Has timestamp
    
    # Verify the metrics reflect the new positive content
    assert updated_metrics.sentiment_score > 0  # Should be positive sentiment
    assert updated_metrics.emotion_scores["emotions"]["joy"] > updated_metrics.emotion_scores["emotions"]["sadness"]  # Joy should be higher than sadness

def test_readability_calculation(linguistic_service):
    """Test readability score calculation"""
    simple_text = "The cat sat on the mat. It was happy."
    complex_text = "The intricate interplay between quantum mechanical phenomena and macroscopic observations presents a fascinating paradox that challenges our fundamental understanding of reality."
    
    simple_metrics = linguistic_service.analyze_text(simple_text)
    complex_metrics = linguistic_service.analyze_text(complex_text)
    
    # Complex text should have higher readability level
    assert complex_metrics["readability_level"] > simple_metrics["readability_level"]

def test_vocabulary_diversity(linguistic_service):
    """Test vocabulary diversity calculation"""
    repetitive_text = "The cat sat. The cat slept. The cat ate."
    diverse_text = "The agile feline gracefully leaped across the ancient stone wall while birds chirped melodiously."
    
    repetitive_metrics = linguistic_service.analyze_text(repetitive_text)
    diverse_metrics = linguistic_service.analyze_text(diverse_text)
    
    # Diverse text should have higher vocabulary diversity
    assert diverse_metrics["vocabulary_diversity_score"] > repetitive_metrics["vocabulary_diversity_score"] 