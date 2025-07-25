from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Table, LargeBinary, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import random

Base = declarative_base()

# Junction table for Log-Tag many-to-many relationship
tag_log_association = Table(
    'tag_log',
    Base.metadata,
    Column('tag_id', UUID, ForeignKey('tags.id'), primary_key=True),
    Column('log_id', UUID, ForeignKey('logs.id'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False),
    UniqueConstraint('tag_id', 'log_id', name='uq_tag_log')
)

class Log(Base):
    __tablename__ = 'logs'

    id = Column(UUID, primary_key=True)  # No default, will be provided by client
    weaviate_id = Column(String, unique=True, nullable=True)  # Store Weaviate ID separately
    content = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Processing metadata
    word_count = Column(Integer, nullable=True)
    processing_status = Column(String, nullable=True)  # 'pending', 'processed', 'failed'

    # Relationships
    tags = relationship('Tag', secondary=tag_log_association, back_populates='logs')
    query_results = relationship('QueryResult', back_populates='log', cascade='all, delete-orphan')

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    color = Column(String, nullable=True)  # hex color for UI

    # Relationships
    logs = relationship('Log', secondary=tag_log_association, back_populates='tags')

    @staticmethod
    def generate_random_color() -> str:
        """Generate a random color hex string matching the client's implementation"""
        r = random.uniform(0.2, 0.9)
        g = random.uniform(0.2, 0.9)
        b = random.uniform(0.2, 0.9)
        return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

    @classmethod
    def get_or_create(cls, db, name: str, color: str = None):
        """Get an existing tag by name or create a new one if it doesn't exist
        
        Args:
            db: Database session
            name: Tag name
            color: Optional hex color string from client
        """
        # Normalize the tag name
        normalized_name = name.strip()
        
        # Try to find existing tag
        existing_tag = db.query(cls).filter(cls.name == normalized_name).first()
        if existing_tag:
            existing_tag.last_used_at = datetime.utcnow()
            # Update color if provided and different from current
            if color and existing_tag.color != color:
                existing_tag.color = color
            return existing_tag
        
        # Create new tag if it doesn't exist
        new_tag = cls(
            name=normalized_name,
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

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    query_text = Column(String, nullable=False)
    embedding = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    execution_time = Column(Float, nullable=True)  # in seconds
    result_count = Column(Integer, nullable=True)

    # Relationships
    results = relationship('QueryResult', back_populates='query', cascade='all, delete-orphan')

class QueryResult(Base):
    __tablename__ = 'query_results'

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    relevance_score = Column(Float, nullable=False, index=True)
    snippet_text = Column(String, nullable=False)
    snippet_start_index = Column(Integer, nullable=False)
    snippet_end_index = Column(Integer, nullable=False)
    context_before = Column(String, nullable=True)
    context_after = Column(String, nullable=True)
    rank = Column(Integer, nullable=False, index=True)

    # Foreign Keys
    query_id = Column(UUID, ForeignKey('queries.id'), nullable=False)
    log_id = Column(UUID, ForeignKey('logs.id'), nullable=False)

    # Relationships
    query = relationship('Query', back_populates='results')
    log = relationship('Log', back_populates='query_results') 