from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Optional
from app.database import get_db
from app.services.session_service import session_service
from app.api.auth import get_current_user
from app.models.models import User
from app.schemas.sessions import SessionCreate, SessionResponse
from datetime import datetime

router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={404: {"description": "Not found"}}
)

@router.post("/start", response_model=SessionResponse)
def start_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start a new writing session"""
    session = session_service.start_session(db, str(current_user.id), session_data.session_type)
    return session

@router.post("/end/{session_id}", response_model=SessionResponse)
def end_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """End a writing session"""
    session = session_service.end_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to end this session")
    return session

@router.get("/active", response_model=Optional[SessionResponse])
def get_active_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the user's active writing session if one exists"""
    return session_service.get_active_session(db, str(current_user.id))

@router.post("/interrupt/{session_id}", response_model=SessionResponse)
def record_interruption(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record an interruption in the writing session"""
    session = session_service.record_interruption(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or already ended")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to modify this session")
    return session

@router.get("/stats", response_model=Dict)
def get_session_stats(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get writing session statistics"""
    return session_service.get_session_stats(db, str(current_user.id), days) 