from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from uuid import UUID
from pydantic import UUID4

from ..models.models import User
from ..schemas.user import UserCreate, UserResponse
from ..utils.uuid_utils import ensure_uuid

import os

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable not set")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_user(db: Session, user_create: UserCreate) -> User:
    """Create a new user."""
    hashed_password = get_password_hash(user_create.password)
    db_user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        display_name=user_create.display_name,
        timezone=user_create.timezone,
        locale=user_create.locale,
        daily_word_goal=user_create.daily_word_goal,
        writing_reminder_time=user_create.writing_reminder_time,
        theme_preferences=user_create.theme_preferences,
        ai_features_enabled=user_create.ai_features_enabled
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def get_user(db: Session, user_id: str) -> Optional[User]:
    """Get user by ID."""
    try:
        uuid_obj = UUID(user_id)
        return db.query(User).filter(User.id == uuid_obj).first()
    except ValueError:
        return None

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()

def update_user(db: Session, user: User, update_data: dict) -> User:
    """Update user data."""
    for key, value in update_data.items():
        if key == "password" and value:
            value = get_password_hash(value)
            key = "hashed_password"
        if hasattr(user, key):
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user 