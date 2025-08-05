import requests
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.models import Theme, Log, log_theme_association

from numpy.linalg import norm

class ThemeService:
    def __init__(self, debug: bool = False):
        """Initialize the theme service"""
        self.debug = debug
        
    def _get_embeddings(self, text: str) -> List[float]:
        """Get embeddings from Ollama API"""
        if self.debug:
            print(f"\n[DEBUG] Getting embeddings for text: {text[:100]}...")
        
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "snowflake-arctic-embed2",
                "prompt": text
            }
        )
        if response.status_code == 200:
            embedding = response.json()["embedding"]
            if self.debug:
                print(f"[DEBUG] Embedding generated successfully. Dimension: {len(embedding)}")
            return embedding
        else:
            print(f"[ERROR] Failed to get embeddings. Status: {response.status_code}")
            print(f"[ERROR] Response: {response.text}")
            raise Exception(f"Failed to get embeddings: {response.text}")
            
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        # Convert to numpy arrays
        a = np.array(embedding1)
        b = np.array(embedding2)
        # Calculate cosine similarity
        return np.dot(a, b) / (norm(a) * norm(b))
        
    def detect_themes(self, text: str, themes: List[Theme], confidence_threshold: float = 0.3) -> List[Dict]:
        """
        Detect themes in text using semantic similarity
        
        Args:
            text: Text content to analyze
            themes: List of available themes to match against
            confidence_threshold: Minimum confidence score to include a theme
            
        Returns:
            List of dicts containing theme and confidence score
        """
        
        if not text or not themes:
            return []
            
        # Get embeddings for input text
        text_embedding = self._get_embeddings(text.lower())
        
        # Process and compare each theme
        theme_matches = []
        for theme in themes:
            # Get theme text (description or name)
            theme_text = theme.description.lower() if theme.description else theme.name.lower()
            theme_embedding = self._get_embeddings(theme_text)
            
            # Calculate similarity
            similarity = self._calculate_similarity(text_embedding, theme_embedding)
            print(f"Theme '{theme.name}' similarity: {similarity}")
            
            if similarity >= confidence_threshold:
                theme_matches.append({
                    "theme": theme,
                    "confidence_score": float(similarity)
                })
                
        # Sort by confidence score
        theme_matches.sort(key=lambda x: x["confidence_score"], reverse=True)
        return theme_matches
        
    def process_log(self, db: Session, log: Log) -> List[Dict]:
        """
        Process a log entry and detect its themes
        
        Args:
            db: Database session
            log: Log entry to process
            
        Returns:
            List of detected themes with confidence scores
        """
        if not log.content:
            return []
            
        # Get all available themes for the user
        themes = db.query(Theme).filter_by(user_id=log.user_id).all()
        
        # Detect themes
        theme_matches = self.detect_themes(log.content, themes)
        
        # Update theme associations
        self._update_theme_associations(db, log, theme_matches)
        
        return theme_matches
        
    def _update_theme_associations(self, db: Session, log: Log, theme_matches: List[Dict]):
        """Update theme associations for a log entry"""
        # Remove existing associations
        db.query(log_theme_association).filter_by(log_id=log.id).delete()
        
        # Add new associations
        for match in theme_matches:
            theme = match["theme"]
            confidence_score = match["confidence_score"]
            
            # Create association with confidence score
            db.execute(
                log_theme_association.insert().values(
                    log_id=log.id,
                    theme_id=theme.id,
                    confidence_score=confidence_score,
                    detected_at=datetime.utcnow()
                )
            )
        
        db.commit()
        
    def create_theme(self, db: Session, user_id: str, name: str, description: Optional[str] = None) -> Theme:
        """
        Create a new theme for a user or update existing one
        
        Args:
            db: Database session
            user_id: ID of the user creating the theme
            name: Theme name
            description: Optional theme description
            
        Returns:
            Created or updated Theme instance
        """
        # Check if theme already exists for this user
        existing_theme = db.query(Theme).filter_by(
            user_id=user_id,
            name=name
        ).first()

        if existing_theme:
            # Update description if provided and different
            if description is not None and existing_theme.description != description:
                existing_theme.description = description
                db.commit()
                db.refresh(existing_theme)
            return existing_theme

        # Create new theme
        theme = Theme(
            user_id=user_id,
            name=name,
            description=description
        )
        
        try:
            db.add(theme)
            db.commit()
            db.refresh(theme)
            return theme
        except IntegrityError:
            db.rollback()
            # In case of race condition, try to fetch the theme again
            return db.query(Theme).filter_by(
                user_id=user_id,
                name=name
            ).first()

    def get_user_themes(self, db: Session, user_id: str) -> List[Theme]:
        """
        Get all themes for a user
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            List of themes belonging to the user
        """
        return db.query(Theme).filter_by(user_id=user_id).all()

    def get_theme(self, db: Session, theme_id: str, user_id: str) -> Optional[Theme]:
        """
        Get a specific theme for a user
        
        Args:
            db: Database session
            theme_id: ID of the theme
            user_id: ID of the user
            
        Returns:
            Theme if found and belongs to user, None otherwise
        """
        return db.query(Theme).filter_by(id=theme_id, user_id=user_id).first()
        
    def get_theme_suggestions(self, db: Session, text: str, user_id: str, max_suggestions: int = 5) -> List[str]:
        """
        Generate theme suggestions based on text content using semantic similarity
        
        Args:
            db: Database session
            text: Text content to analyze
            user_id: ID of the user
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            List of suggested theme names
        """
        if not text:
            return []
            
        # Get embeddings for the input text
        text_embedding = self._get_embeddings(text.lower())
        
        # Get existing themes for comparison
        existing_themes = self.get_user_themes(db, user_id)
        existing_names = {theme.name.lower() for theme in existing_themes}
        
        # Generate candidate phrases using an LLM
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": (
                    "Extract potential themes from this text. Focus on topics, emotions, or areas of life mentioned. "
                    "Return ONLY a list of 10 short, concise themes (1-3 words each), one per line. No numbers, bullets, or explanations.\n\n"
                    f"Text: {text}\n\n"
                    "Themes:"
                ),
                "stream": False
            }
        )
        
        if response.status_code != 200:
            print(f"[ERROR] Failed to generate themes. Status: {response.status_code}")
            return []
            
        # Parse response and get unique suggestions
        suggestions = response.json()["response"].strip().split("\n")
        suggestions = [s.strip().lower() for s in suggestions if s.strip()]
        suggestions = [s for s in suggestions if s not in existing_names]
        
        if self.debug:
            print(f"\n[DEBUG] Generated theme suggestions: {suggestions}")
        
        # Score suggestions by similarity to the text
        scored_suggestions = []
        for suggestion in suggestions:
            suggestion_embedding = self._get_embeddings(suggestion)
            similarity = self._calculate_similarity(text_embedding, suggestion_embedding)
            scored_suggestions.append((suggestion, similarity))
            if self.debug:
                print(f"[DEBUG] Theme '{suggestion}' similarity: {similarity}")
            
        # Sort by similarity score and return top suggestions
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)
        return [suggestion for suggestion, _ in scored_suggestions[:max_suggestions]]

# Create global instance
theme_service = ThemeService() 