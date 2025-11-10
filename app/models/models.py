from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Table, LargeBinary, UniqueConstraint, JSON, Boolean, CheckConstraint, Enum, Text, Index
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import random
from app.utils.uuid_utils import ensure_uuid4
from pydantic import UUID4
import sqlalchemy as sa

Base = declarative_base()

# Junction table for Log-Tag many-to-many relationship
tag_log_association = Table(
    'tag_log',
    Base.metadata,
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'), primary_key=True),
    Column('log_id', UUID(as_uuid=True), ForeignKey('logs.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
    UniqueConstraint('tag_id', 'log_id', name='uq_tag_log')
)

# Junction table for Log-Theme many-to-many relationship
log_theme_association = Table(
    'log_theme',
    Base.metadata,
    Column('theme_id', UUID(as_uuid=True), ForeignKey('themes.id'), primary_key=True),
    Column('log_id', UUID(as_uuid=True), ForeignKey('logs.id'), primary_key=True),
    Column('confidence_score', Float, nullable=False),
    Column('detected_at', DateTime, default=datetime.utcnow, nullable=False),
    UniqueConstraint('theme_id', 'log_id', name='uq_theme_log')
)

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String)
    timezone = Column(String, default='UTC')
    locale = Column(String, default='en-US')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User preferences
    daily_word_goal = Column(Integer, default=750)
    writing_reminder_time = Column(String)  # Store as HH:MM in UTC
    theme_preferences = Column(JSON)  # Store UI/theme preferences
    ai_features_enabled = Column(Boolean, default=True)

    # Privacy tier settings
    privacy_tier = Column(
        Enum('local_only', 'analytics_sync', 'full_sync', name='privacy_tier_enum'),
        default='local_only',
        nullable=False
    )
    he_public_key = Column(Text, nullable=True)
    sync_enabled_at = Column(DateTime, nullable=True)

    # Relationships with cascade delete
    logs = relationship('Log', back_populates='user', cascade='all, delete-orphan')
    writing_sessions = relationship('WritingSession', back_populates='user', cascade='all, delete-orphan')
    prompts = relationship('Prompt', back_populates='user', cascade='all, delete-orphan')
    insights = relationship('UserInsight', back_populates='user', cascade='all, delete-orphan')
    queries = relationship('Query', back_populates='user', cascade='all, delete-orphan')
    themes = relationship('Theme', back_populates='user', cascade='all, delete-orphan')
    tags = relationship('Tag', back_populates='user', cascade='all, delete-orphan')
    encrypted_metrics = relationship('EncryptedMetric', back_populates='user', cascade='all, delete-orphan')

class WritingSession(Base):
    __tablename__ = 'writing_sessions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    session_type = Column(String)  # 'daily', 'freeform', 'prompted'
    interruption_count = Column(Integer, default=0)
    focus_score = Column(Float)
    
    # Relationships
    user = relationship('User', back_populates='writing_sessions')
    logs = relationship('Log', back_populates='writing_session')

class LinguisticMetrics(Base):
    __tablename__ = 'linguistic_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(UUID(as_uuid=True), ForeignKey('logs.id'), nullable=False)
    vocabulary_diversity_score = Column(Float)
    sentiment_score = Column(Float)
    complexity_score = Column(Float)
    readability_level = Column(Float)
    emotion_scores = Column(JSON)  # Store detailed emotion analysis
    writing_style_metrics = Column(JSON)  # Store style-related metrics
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    log = relationship('Log', back_populates='linguistic_metrics')

class Theme(Base):
    __tablename__ = 'themes'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    confidence_threshold = Column(Float, default=0.7)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='themes')
    logs = relationship('Log', secondary=log_theme_association, back_populates='themes')

    # Add unique constraint for name per user
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_theme_name'),
    )

class EntryRevision(Base):
    __tablename__ = 'entry_revisions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    log_id = Column(UUID(as_uuid=True), ForeignKey('logs.id'), nullable=False)
    revision_number = Column(Integer, nullable=False)
    content_delta = Column(JSON, nullable=False)  # Store the change delta
    revision_type = Column(String)  # 'addition', 'strikethrough', 'formatting'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    log = relationship('Log', back_populates='revisions')

class Prompt(Base):
    __tablename__ = 'prompts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    prompt_text = Column(String, nullable=False)
    prompt_type = Column(String)  # e.g., 'daily', 'reflection', 'growth'
    effectiveness_score = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    generation_context = Column(JSON)  # Store context used to generate this prompt
    
    # Relationships
    user = relationship('User', back_populates='prompts')
    logs = relationship('Log', back_populates='prompt')

class UserInsight(Base):
    __tablename__ = 'user_insights'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    insight_type = Column(String, nullable=False)  # e.g., 'vocabulary', 'consistency', 'theme'
    insight_data = Column(JSON, nullable=False)
    date_range_start = Column(DateTime, nullable=False)
    date_range_end = Column(DateTime, nullable=False)
    confidence_score = Column(Float)
    status = Column(String, default='new')  # 'new', 'viewed', 'dismissed'
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', back_populates='insights')

class Log(Base):
    __tablename__ = 'logs'

    id = Column(UUID(as_uuid=True), primary_key=True)  # No default, will be provided by client
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey('writing_sessions.id'), nullable=True)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey('prompts.id'), nullable=True)
    weaviate_id = Column(String, unique=True, nullable=True)  # Store Weaviate ID separately
    content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # New fields
    mood_score = Column(Float)  # -1 to 1 scale
    completion_status = Column(String, default='draft')  # 'draft', 'complete', 'archived'
    target_word_count = Column(Integer, default=750)
    writing_duration = Column(Integer)  # seconds spent writing
    
    # Processing metadata
    word_count = Column(Integer, nullable=True)
    processing_status = Column(String, nullable=True)  # 'pending', 'processed', 'failed'

    # Relationships with cascade delete
    user = relationship('User', back_populates='logs')
    writing_session = relationship('WritingSession', back_populates='logs')
    prompt = relationship('Prompt', back_populates='logs')
    tags = relationship('Tag', secondary=tag_log_association, back_populates='logs')
    themes = relationship('Theme', secondary=log_theme_association, back_populates='logs')
    query_results = relationship('QueryResult', back_populates='log', cascade='all, delete-orphan')
    linguistic_metrics = relationship('LinguisticMetrics', back_populates='log', cascade='all, delete-orphan', uselist=False)
    revisions = relationship('EntryRevision', back_populates='log', cascade='all, delete-orphan', order_by='EntryRevision.revision_number')

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    color = Column(String, nullable=True)  # hex color for UI

    # Relationships
    user = relationship('User', back_populates='tags')
    logs = relationship('Log', secondary=tag_log_association, back_populates='tags')

    # Add unique constraint for name per user
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_tag_name'),
    )

    @staticmethod
    def generate_random_color() -> str:
        """Generate a random color hex string matching the client's implementation"""
        r = random.uniform(0.2, 0.9)
        g = random.uniform(0.2, 0.9)
        b = random.uniform(0.2, 0.9)
        return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

    @classmethod
    def get_or_create(cls, db, name: str, user_id, color: str = None):
        """Get an existing tag by name for a user or create a new one if it doesn't exist

        Args:
            db: Database session
            name: Tag name
            user_id: User ID (UUID)
            color: Optional hex color string from client
        """
        # Normalize the tag name
        normalized_name = name.strip()

        # Try to find existing tag for this user
        existing_tag = db.query(cls).filter(
            cls.name == normalized_name,
            cls.user_id == user_id
        ).first()
        if existing_tag:
            existing_tag.last_used_at = datetime.utcnow()
            # Update color if provided and different from current
            if color and existing_tag.color != color:
                existing_tag.color = color
            return existing_tag

        # Create new tag if it doesn't exist for this user
        new_tag = cls(
            name=normalized_name,
            user_id=user_id,
            last_used_at=datetime.utcnow(),
            color=color if color else cls.generate_random_color()  # Use provided color or generate new one
        )
        db.add(new_tag)
        return new_tag

    def mark_used(self):
        """Update the last_used_at timestamp"""
        self.last_used_at = datetime.utcnow()

class Query(Base):
    __tablename__ = 'queries'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    query_text = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    execution_time = Column(Float, nullable=True)  # in seconds
    result_count = Column(Integer, nullable=True)

    # Relationships
    user = relationship('User', back_populates='queries')
    results = relationship('QueryResult', back_populates='query', cascade='all, delete-orphan')

class QueryResult(Base):
    __tablename__ = 'query_results'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    relevance_score = Column(Float, nullable=False, index=True)
    snippet_text = Column(String, nullable=False)
    snippet_start_index = Column(Integer, nullable=False)
    snippet_end_index = Column(Integer, nullable=False)
    context_before = Column(String, nullable=True)
    context_after = Column(String, nullable=True)
    rank = Column(Integer, nullable=False, index=True)

    # Foreign Keys
    query_id = Column(UUID(as_uuid=True), ForeignKey('queries.id'), nullable=False)
    log_id = Column(UUID(as_uuid=True), ForeignKey('logs.id'), nullable=False)

    # Relationships
    query = relationship('Query', back_populates='results')
    log = relationship('Log', back_populates='query_results')

class EncryptedMetric(Base):
    __tablename__ = 'encrypted_metrics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    metric_type = Column(String, nullable=False)
    encrypted_value = Column(LargeBinary, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', back_populates='encrypted_metrics')

    # Indexes for query performance
    __table_args__ = (
        Index('ix_encrypted_metrics_user_type_time', 'user_id', 'metric_type', 'timestamp'),
    ) 