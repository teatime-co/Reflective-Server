from typing import Dict, Optional, List
import spacy
from textblob import TextBlob
import numpy as np
from numpy.linalg import norm
import requests
from app.models.models import LinguisticMetrics, Log
from sqlalchemy.orm import Session
from datetime import datetime

class LinguisticService:
    def __init__(self):
        """Initialize the linguistic service with NLP models"""
        # Load spaCy model for advanced NLP tasks
        self.nlp = spacy.load("en_core_web_sm")
        self.debug = True
        
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
    
    def analyze_text(self, text: str) -> Dict:
        """
        Analyze text and return linguistic metrics
        
        Args:
            text: The text content to analyze
            
        Returns:
            Dict containing linguistic metrics
        """
        # Handle empty text
        if not text.strip():
            return {
                "vocabulary_diversity_score": 0.0,
                "sentiment_score": 0.0,
                "complexity_score": 0.0,
                "readability_level": 0.0,
                "emotion_scores": {
                    "emotions": {
                        "joy": 0.0,
                        "sadness": 0.0,
                        "anger": 0.0,
                        "fear": 0.0,
                        "surprise": 0.0
                    },
                    "subjectivity": 0.0
                },
                "writing_style_metrics": {
                    "sentence_types": {
                        "declarative": 0.0,
                        "interrogative": 0.0,
                        "exclamatory": 0.0
                    },
                    "style_similarities": {
                        "formal": 0.0,
                        "casual": 0.0,
                        "technical": 0.0,
                        "narrative": 0.0,
                        "persuasive": 0.0
                    },
                    "formality_indicators": {
                        "academic_words": 0.0,
                        "personal_pronouns": 0.0
                    }
                }
            }
            
        # Basic text preprocessing
        doc = self.nlp(text)
        blob = TextBlob(text)
        
        # Calculate metrics
        metrics = {
            "vocabulary_diversity_score": self._calculate_vocabulary_diversity(doc),
            "sentiment_score": blob.sentiment.polarity,
            "complexity_score": self._calculate_complexity_score(doc),
            "readability_level": self._calculate_readability_level(doc),
            "emotion_scores": self._analyze_emotions(text),
            "writing_style_metrics": self._analyze_writing_style(doc)
        }
        
        return metrics
    
    def process_log(self, db: Session, log: Log) -> Optional[LinguisticMetrics]:
        """
        Process a log entry and store its linguistic metrics
        
        Args:
            db: Database session
            log: Log entry to process
            
        Returns:
            Created LinguisticMetrics instance
        """
        # Skip if no content
        if not log.content:
            return None
            
        # Get metrics
        metrics = self.analyze_text(log.content)
        
        # Create or update metrics
        linguistic_metrics = log.linguistic_metrics or LinguisticMetrics(log_id=log.id)
        
        # Store old processed_at if updating
        old_processed_at = linguistic_metrics.processed_at if linguistic_metrics.id else None
        
        # Update all fields
        for key, value in metrics.items():
            setattr(linguistic_metrics, key, value)
        
        # Ensure new timestamp is always greater than old one
        new_processed_at = datetime.utcnow()
        if old_processed_at and new_processed_at <= old_processed_at:
            # If new timestamp would be less than or equal to old one,
            # explicitly set it to 1 microsecond after the old timestamp
            new_processed_at = datetime.fromtimestamp(
                old_processed_at.timestamp() + 0.000001
            )
        linguistic_metrics.processed_at = new_processed_at
        
        # Save if new
        if not linguistic_metrics.id:
            db.add(linguistic_metrics)
            
        # Always commit changes
        db.commit()
        db.refresh(linguistic_metrics)
        
        return linguistic_metrics
    
    def _calculate_vocabulary_diversity(self, doc) -> float:
        """Calculate vocabulary diversity using type-token ratio"""
        tokens = [token.text.lower() for token in doc if not token.is_punct and not token.is_space]
        if not tokens:
            return 0.0
        return len(set(tokens)) / len(tokens)
    
    def _calculate_complexity_score(self, doc) -> float:
        """Calculate text complexity using semantic embeddings and traditional metrics"""
        if not doc or len(doc) == 0:
            return 0.0
            
        try:
            # Reference texts of varying complexity
            reference_texts = {
                "simple": "The cat sat on the mat. The sun was bright. The birds flew in the sky. It was a nice day.",
                "moderate": "The relationship between cause and effect is not always straightforward. Various factors can influence outcomes in unexpected ways.",
                "complex": "The intricate interplay between quantum mechanical phenomena and macroscopic observations presents a fascinating paradox that challenges our fundamental understanding of reality.",
                "very_complex": "The epistemological implications of quantum entanglement suggest a fundamental interconnectedness of physical systems that transcends classical notions of locality and causality, compelling us to reevaluate our conception of objective reality."
            }
            
            # Get embeddings
            text_embedding = self._get_embeddings(doc.text)
            reference_embeddings = {
                level: self._get_embeddings(ref_text)
                for level, ref_text in reference_texts.items()
            }
            
            # Calculate similarities with reference texts
            similarities = {
                level: self._calculate_similarity(text_embedding, ref_embedding)
                for level, ref_embedding in reference_embeddings.items()
            }
            
            # Weight the complexity score (higher similarity to complex = higher score)
            semantic_complexity = (
                similarities["very_complex"] * 1.0 +
                similarities["complex"] * 0.75 +
                similarities["moderate"] * 0.25 +
                similarities["simple"] * 0.0
            ) / 2.0  # Divide by 2 since we're adding two top scores
            
            # Traditional metrics as a fallback/supplement
            traditional_metrics = {
                "avg_word_length": sum(len(token.text) for token in doc if not token.is_punct) / len([token for token in doc if not token.is_punct]),
                "avg_sentence_length": len([token for token in doc if not token.is_punct]) / len(list(doc.sents)),
                "complex_words": sum(1 for token in doc if not token.is_punct and self._count_syllables(token.text) >= 3) / len([token for token in doc if not token.is_punct])
            }
            
            # Combine semantic and traditional metrics
            traditional_score = (
                0.4 * (traditional_metrics["avg_word_length"] / 10.0) +  # Normalize by typical max word length
                0.3 * (traditional_metrics["avg_sentence_length"] / 30.0) +  # Normalize by typical max sentence length
                0.3 * traditional_metrics["complex_words"]
            )
            
            # Final score is weighted combination
            final_score = (0.7 * semantic_complexity) + (0.3 * traditional_score)
            
            return max(0.0, min(1.0, final_score))
            
        except Exception as e:
            print(f"[ERROR] Failed to calculate semantic complexity: {str(e)}")
            # Fallback to basic traditional metrics
            try:
                avg_word_length = sum(len(token.text) for token in doc if not token.is_punct) / len([token for token in doc if not token.is_punct])
                avg_sentence_length = len([token for token in doc if not token.is_punct]) / len(list(doc.sents))
                complex_words = sum(1 for token in doc if not token.is_punct and self._count_syllables(token.text) >= 3) / len([token for token in doc if not token.is_punct])
                
                score = (
                    0.4 * (avg_word_length / 10.0) +
                    0.3 * (avg_sentence_length / 30.0) +
                    0.3 * complex_words
                )
                return max(0.0, min(1.0, score))
            except:
                return 0.0
    
    def _calculate_readability_level(self, doc) -> float:
        """Calculate readability using simplified Flesch-Kincaid"""
        sentences = list(doc.sents)
        if not sentences:
            return 0.0
            
        total_words = sum(1 for token in doc if not token.is_punct and not token.is_space)
        total_syllables = sum(self._count_syllables(token.text) for token in doc if not token.is_punct)
        num_sentences = len(sentences)
        
        if num_sentences == 0 or total_words == 0:
            return 0.0
            
        # Simplified Flesch-Kincaid Grade Level
        score = 0.39 * (total_words / num_sentences) + 11.8 * (total_syllables / total_words) - 15.59
        return max(0.0, min(score, 100.0))  # Clamp between 0 and 100
    
    def _count_syllables(self, word: str) -> int:
        """Estimate syllable count for a word"""
        word = word.lower()
        count = 0
        vowels = "aeiouy"
        prev_char_is_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_char_is_vowel:
                count += 1
            prev_char_is_vowel = is_vowel
            
        if word.endswith("e"):
            count -= 1
        if count == 0:
            count = 1
            
        return count
    
    def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """Analyze emotional content using embeddings"""
        if self.debug:
            print(f"\n[DEBUG] Starting emotion analysis for text: {text[:100]}...")
            
        # Emotion anchor texts - using more distinct and focused examples
        emotion_anchors = {
            "joy": "I am overjoyed and ecstatic! Everything is perfect and wonderful! I'm so happy I could dance!",
            "sadness": "I feel completely devastated and heartbroken. Everything is dark and hopeless. I can't stop crying.",
            "anger": "I am absolutely furious and enraged! This is completely unacceptable! I'm so mad I could scream!",
            "fear": "I am terrified and paralyzed with fear. Danger lurks everywhere. I'm trembling with anxiety.",
            "surprise": "I am absolutely shocked and stunned! I can't believe what just happened! This is completely unexpected!"
        }
        
        try:
            if self.debug:
                print("[DEBUG] Getting text embedding...")
            # Get embeddings for input text
            text_embedding = self._get_embeddings(text)
            
            if self.debug:
                print("[DEBUG] Getting emotion anchor embeddings...")
            # Get embeddings for emotion anchors
            emotion_embeddings = {
                emotion: self._get_embeddings(anchor_text)
                for emotion, anchor_text in emotion_anchors.items()
            }
            
            if self.debug:
                print("[DEBUG] Calculating emotion similarities...")
            # Calculate similarities and apply softmax-like normalization
            similarities = {
                emotion: self._calculate_similarity(text_embedding, emotion_embedding)
                for emotion, emotion_embedding in emotion_embeddings.items()
            }
            
            if self.debug:
                print("\n[DEBUG] Raw emotion similarities:")
                for emotion, score in similarities.items():
                    print(f"[DEBUG] - {emotion}: {score:.3f}")
            
            # Apply exponential scaling to amplify differences
            exp_similarities = {
                emotion: np.exp(4 * score)  # Scale factor of 4 to amplify differences
                for emotion, score in similarities.items()
            }
            
            if self.debug:
                print("\n[DEBUG] After exponential scaling:")
                for emotion, score in exp_similarities.items():
                    print(f"[DEBUG] - {emotion}: {score:.3f}")
            
            # Normalize to get final scores
            total = sum(exp_similarities.values())
            emotion_scores = {
                emotion: score / total if total > 0 else 0.0
                for emotion, score in exp_similarities.items()
            }
            
            if self.debug:
                print("\n[DEBUG] Final normalized emotion scores:")
                for emotion, score in emotion_scores.items():
                    print(f"[DEBUG] - {emotion}: {score:.3f}")
            
            # Calculate subjectivity using embeddings
            if self.debug:
                print("\n[DEBUG] Calculating subjectivity score...")
                
            objective_anchor = "The sky is blue. Water freezes at 0 degrees Celsius. The Earth orbits the Sun."
            subjective_anchor = "This is the most amazing thing ever! I absolutely love how beautiful and perfect everything is!"
            
            obj_embedding = self._get_embeddings(objective_anchor)
            subj_embedding = self._get_embeddings(subjective_anchor)
            
            obj_sim = self._calculate_similarity(text_embedding, obj_embedding)
            subj_sim = self._calculate_similarity(text_embedding, subj_embedding)
            
            # Calculate subjectivity score (0 = objective, 1 = subjective)
            subjectivity = subj_sim / (obj_sim + subj_sim) if (obj_sim + subj_sim) > 0 else 0.5
            
            if self.debug:
                print(f"[DEBUG] Objective similarity: {obj_sim:.3f}")
                print(f"[DEBUG] Subjective similarity: {subj_sim:.3f}")
                print(f"[DEBUG] Final subjectivity score: {subjectivity:.3f}")
            
            return {
                "emotions": emotion_scores,
                "subjectivity": subjectivity
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to analyze emotions: {str(e)}")
            if self.debug:
                print(f"[DEBUG] Full error details: {e.__class__.__name__}: {str(e)}")
            return {
                "emotions": {emotion: 0.0 for emotion in emotion_anchors.keys()},
                "subjectivity": 0.0
            }
    
    def _analyze_writing_style(self, doc) -> Dict:
        """Analyze writing style metrics using both traditional NLP and embeddings"""
        if not doc:
            return {}
            
        # Traditional sentence type analysis
        sentence_types = {
            "declarative": 0,
            "interrogative": 0,
            "exclamatory": 0
        }
        
        total_sentences = 0
        for sent in doc.sents:
            total_sentences += 1
            text = sent.text.strip()
            if text.endswith("?"):
                sentence_types["interrogative"] += 1
            elif text.endswith("!"):
                sentence_types["exclamatory"] += 1
            else:
                sentence_types["declarative"] += 1
                
        # Calculate traditional style metrics
        traditional_metrics = {
            "avg_sentence_length": len(doc) / total_sentences if total_sentences > 0 else 0,
            "sentence_types": {k: v/total_sentences if total_sentences > 0 else 0 
                             for k, v in sentence_types.items()},
            "formality_indicators": {
                "academic_words": len([token for token in doc 
                    if token.is_alpha and len(token.text) > 6]) / len(doc),
                "personal_pronouns": len([token for token in doc 
                    if token.pos_ == "PRON"]) / len(doc)
            }
        }
        
        try:
            # Add embedding-based style analysis
            style_anchors = {
                "formal": "This document presents a comprehensive analysis of the subject matter. The methodology employed demonstrates rigorous attention to detail.",
                "casual": "Hey! Just wanted to share some quick thoughts about this. It's pretty cool how everything worked out.",
                "technical": "The system architecture implements a microservices pattern with containerized deployments. The API endpoints utilize REST principles.",
                "narrative": "The sun was setting as she walked along the beach, memories of that summer flooding back. Each wave brought a new story.",
                "persuasive": "It is crucial that we consider the implications of this decision. The evidence clearly shows the benefits outweigh the costs."
            }
            
            # Get embeddings for the full text
            text_embedding = self._get_embeddings(doc.text)
            
            # Get embeddings for style anchors
            style_embeddings = {
                style: self._get_embeddings(anchor_text)
                for style, anchor_text in style_anchors.items()
            }
            
            # Calculate style similarities
            style_scores = {
                style: self._calculate_similarity(text_embedding, style_embedding)
                for style, style_embedding in style_embeddings.items()
            }
            
            # Combine traditional and embedding-based metrics
            return {
                **traditional_metrics,
                "style_similarities": style_scores
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to analyze writing style with embeddings: {str(e)}")
            # Fallback to traditional metrics only
            return traditional_metrics

# Create global instance
linguistic_service = LinguisticService() 