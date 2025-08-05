from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from app.database import get_db
from app.services.linguistic_service import linguistic_service
from app.api.auth import get_current_user
from app.models.models import User, Log
from app.schemas.linguistic import (
    TextAnalysis,
    LinguisticMetricsResponse
)
from datetime import datetime
from uuid import UUID

router = APIRouter(
    prefix="/linguistic",
    tags=["linguistic"],
    responses={404: {"description": "Not found"}}
)

@router.post("/analyze", response_model=TextAnalysis)
def analyze_text(
    analysis: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze text and return linguistic metrics"""
    if not analysis or "text" not in analysis:
        raise HTTPException(status_code=422, detail="Text field is required")
    return linguistic_service.analyze_text(analysis["text"])

@router.post("/process/{log_id}", response_model=LinguisticMetricsResponse)
def process_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate UUID format
        log_uuid = UUID(log_id)
        
        log = db.query(Log).filter_by(id=log_uuid).first()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        if str(log.user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this log")
            
        metrics = linguistic_service.process_log(db, log)
        if not metrics:
            raise HTTPException(status_code=422, detail="Could not process log content")
        
        return metrics
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid log ID format")

@router.get("/metrics/{log_id}", response_model=LinguisticMetricsResponse)
def get_metrics(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Validate UUID format
        log_uuid = UUID(log_id)
        
        log = db.query(Log).filter_by(id=log_uuid).first()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        if str(log.user_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to access this log")
            
        metrics = log.linguistic_metrics
        if not metrics:
            raise HTTPException(status_code=404, detail="No linguistic metrics found for this log")
            
        return metrics
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid log ID format") 