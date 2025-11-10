from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import JWTError, jwt
from pydantic import UUID4

from ..database import get_db
from ..models.models import Log
from ..services.auth_service import (
    authenticate_user, create_user, get_user_by_email,
    create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM,
    get_user
)
from ..schemas.user import UserCreate, UserResponse, Token, TokenData
from ..utils.uuid_utils import ensure_uuid4

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> UserResponse:
    """Get current user from JWT token."""
    print(f"[DEBUG] get_current_user called with token: {token[:20]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        print(f"[DEBUG] Decoded JWT - user_id: {user_id}, email: {email}")

        if user_id is None:
            print("[DEBUG] user_id is None, raising exception")
            raise credentials_exception

        token_data = TokenData(user_id=ensure_uuid4(user_id), email=email)
    except (JWTError, ValueError) as e:
        print(f"[DEBUG] JWT decode failed: {e}")
        raise credentials_exception
    
    # First try to get user by ID (primary method)
    user = get_user(db, token_data.user_id)
    
    # If user not found by ID and we have an email, try by email as fallback
    if user is None and token_data.email:
        user = get_user_by_email(db, token_data.email)
    
    if user is None:
        raise credentials_exception

    try:
        logs_count = db.query(Log).filter(Log.user_id == user.id).count()
        total_words_result = db.query(func.sum(Log.word_count)).filter(Log.user_id == user.id).scalar()
        total_words = int(total_words_result) if total_words_result else 0
    except Exception as e:
        print(f"Error calculating stats: {e}")
        logs_count = 0
        total_words = 0

    try:
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            timezone=user.timezone,
            locale=user.locale,
            privacy_tier=user.privacy_tier,
            daily_word_goal=user.daily_word_goal,
            writing_reminder_time=user.writing_reminder_time,
            theme_preferences=user.theme_preferences,
            ai_features_enabled=user.ai_features_enabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
            logs_count=logs_count,
            writing_streak=0,
            total_words_written=total_words
        )
        return user_response
    except Exception as e:
        print(f"Error creating UserResponse: {e}")
        print(f"User data: id={user.id}, privacy_tier={user.privacy_tier}")
        raise credentials_exception

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return create_user(db=db, user_create=user)

@router.post("/token", response_model=Token, status_code=status.HTTP_200_OK)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db)
):
    """Login to get access token."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"} 