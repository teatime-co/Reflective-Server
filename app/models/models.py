from __future__ import annotations

from typing import Dict, Any
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Table, LargeBinary, UniqueConstraint, JSON, Boolean, CheckConstraint, Enum, Text, Index
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import random
from app.utils.uuid_utils import ensure_uuid4
from pydantic import UUID4
import sqlalchemy as sa

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
    display_name: Mapped[str | None] = mapped_column(String)
    timezone: Mapped[str] = mapped_column(String, default='UTC')
    locale: Mapped[str] = mapped_column(String, default='en-US')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # User preferences
    daily_word_goal: Mapped[int] = mapped_column(Integer, default=750)
    writing_reminder_time: Mapped[str | None] = mapped_column(String)
    theme_preferences: Mapped[dict | None] = mapped_column(JSON)
    ai_features_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Privacy tier settings
    privacy_tier: Mapped[str] = mapped_column(
        Enum('local_only', 'analytics_sync', 'full_sync', name='privacy_tier_enum'),
        default='local_only'
    )
    he_public_key: Mapped[str | None] = mapped_column(Text)
    sync_enabled_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships with cascade delete (encrypted architecture only)
    tags: Mapped[list[Tag]] = relationship('Tag', back_populates='user', cascade='all, delete-orphan')
    encrypted_metrics: Mapped[list[EncryptedMetric]] = relationship('EncryptedMetric', back_populates='user', cascade='all, delete-orphan')
    encrypted_backups: Mapped[list[EncryptedBackup]] = relationship('EncryptedBackup', back_populates='user', cascade='all, delete-orphan')
    sync_conflicts: Mapped[list[SyncConflict]] = relationship('SyncConflict', back_populates='user', cascade='all, delete-orphan')

class Tag(Base):
    __tablename__ = 'tags'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    color: Mapped[str | None] = mapped_column(String)

    # Relationships
    user: Mapped[User] = relationship('User', back_populates='tags')

    # Add unique constraint for name per user
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_user_tag_name'),
    )

    @staticmethod
    def generate_random_color() -> str:
        r = random.uniform(0.2, 0.9)
        g = random.uniform(0.2, 0.9)
        b = random.uniform(0.2, 0.9)
        return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"

    @classmethod
    def get_or_create(cls, db, name: str, user_id, color: str = None):
        normalized_name = name.strip()

        existing_tag = db.query(cls).filter(
            cls.name == normalized_name,
            cls.user_id == user_id
        ).first()
        if existing_tag:
            existing_tag.last_used_at = datetime.utcnow()
            if color and existing_tag.color != color:
                existing_tag.color = color
            return existing_tag

        new_tag = cls(
            name=normalized_name,
            user_id=user_id,
            last_used_at=datetime.utcnow(),
            color=color if color else cls.generate_random_color()
        )
        db.add(new_tag)
        return new_tag

    def mark_used(self):
        self.last_used_at = datetime.utcnow()

class EncryptedMetric(Base):
    __tablename__ = 'encrypted_metrics'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))

    metric_type: Mapped[str] = mapped_column(String)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary)
    timestamp: Mapped[datetime] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship('User', back_populates='encrypted_metrics')

    # Indexes for query performance
    __table_args__ = (
        Index('ix_encrypted_metrics_user_type_time', 'user_id', 'metric_type', 'timestamp'),
    )

class EncryptedBackup(Base):
    __tablename__ = 'encrypted_backups'

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Encrypted content (AES-256)
    encrypted_content: Mapped[bytes] = mapped_column(LargeBinary)
    content_iv: Mapped[str] = mapped_column(String)
    content_tag: Mapped[str | None] = mapped_column(String)

    # Encrypted embeddings (for cross-device search)
    encrypted_embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    embedding_iv: Mapped[str | None] = mapped_column(String)

    # Metadata (NOT encrypted - for sync coordination)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    device_id: Mapped[str] = mapped_column(String)

    # Relationships
    user: Mapped[User] = relationship('User', back_populates='encrypted_backups')

    # Indexes
    __table_args__ = (
        Index('ix_encrypted_backups_user_updated', 'user_id', 'updated_at'),
        Index('ix_encrypted_backups_device', 'device_id'),
    )

class SyncConflict(Base):
    __tablename__ = 'sync_conflicts'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id'))
    log_id: Mapped[str] = mapped_column(String)

    # Local version (from device requesting sync)
    local_encrypted_content: Mapped[bytes] = mapped_column(LargeBinary)
    local_iv: Mapped[str] = mapped_column(String)
    local_tag: Mapped[str | None] = mapped_column(String)
    local_updated_at: Mapped[datetime] = mapped_column(DateTime)
    local_device_id: Mapped[str] = mapped_column(String)

    # Remote version (from server)
    remote_encrypted_content: Mapped[bytes] = mapped_column(LargeBinary)
    remote_iv: Mapped[str] = mapped_column(String)
    remote_tag: Mapped[str | None] = mapped_column(String)
    remote_updated_at: Mapped[datetime] = mapped_column(DateTime)
    remote_device_id: Mapped[str] = mapped_column(String)

    # Conflict metadata
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user: Mapped[User] = relationship('User', back_populates='sync_conflicts')

    # Indexes
    __table_args__ = (
        Index('ix_sync_conflicts_user_unresolved', 'user_id', 'resolved'),
        Index('ix_sync_conflicts_log_id', 'log_id'),
    )
