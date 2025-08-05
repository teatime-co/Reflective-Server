from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import WritingSession, Log, User

class SessionService:
    def __init__(self):
        """Initialize the session service"""
        self.IDLE_TIMEOUT = timedelta(minutes=30)  # Session considered inactive after 30 mins
        
    def start_session(self, db: Session, user_id: str, session_type: str = "freeform") -> WritingSession:
        """
        Start a new writing session
        
        Args:
            db: Database session
            user_id: ID of the user starting the session
            session_type: Type of writing session ('daily', 'freeform', 'prompted')
            
        Returns:
            Created WritingSession instance
        """
        # Check for existing active session
        active_session = self.get_active_session(db, user_id)
        if active_session:
            # Close existing session if it exists
            self.end_session(db, active_session.id)
            
        # Create new session
        session = WritingSession(
            user_id=user_id,
            started_at=datetime.utcnow(),
            session_type=session_type,
            interruption_count=0
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
        
    def end_session(self, db: Session, session_id: str) -> Optional[WritingSession]:
        """
        End a writing session and calculate metrics
        
        Args:
            db: Database session
            session_id: ID of the session to end
            
        Returns:
            Updated WritingSession instance or None if not found
        """
        session = db.query(WritingSession).filter_by(id=session_id).first()
        if not session or session.ended_at:
            return None
            
        # Set end time
        session.ended_at = datetime.utcnow()
        
        # Calculate focus score
        session.focus_score = self._calculate_focus_score(session)
        
        db.commit()
        db.refresh(session)
        return session
        
    def get_active_session(self, db: Session, user_id: str) -> Optional[WritingSession]:
        """
        Get user's active writing session if it exists
        
        Args:
            db: Database session
            user_id: User ID to check for active session
            
        Returns:
            Active WritingSession instance or None
        """
        # Get most recent session without end time
        session = (db.query(WritingSession)
                  .filter_by(user_id=user_id, ended_at=None)
                  .order_by(WritingSession.started_at.desc())
                  .first())
                  
        if not session:
            return None
            
        # Check if session is still active
        if datetime.utcnow() - session.started_at > self.IDLE_TIMEOUT:
            # Auto-end inactive session
            self.end_session(db, session.id)
            return None
            
        return session
        
    def record_interruption(self, db: Session, session_id: str) -> Optional[WritingSession]:
        """
        Record an interruption in the writing session
        
        Args:
            db: Database session
            session_id: ID of the session to update
            
        Returns:
            Updated WritingSession instance or None if not found
        """
        session = db.query(WritingSession).filter_by(id=session_id).first()
        if not session or session.ended_at:
            return None
            
        session.interruption_count += 1
        db.commit()
        db.refresh(session)
        return session
        
    def get_session_stats(self, db: Session, user_id: str, days: int = 30) -> Dict:
        """
        Get writing session statistics for a user
        
        Args:
            db: Database session
            user_id: User ID to get stats for
            days: Number of days to analyze
            
        Returns:
            Dictionary containing session statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all completed sessions in date range
        sessions = (db.query(WritingSession)
                   .filter(WritingSession.user_id == user_id,
                          WritingSession.started_at >= start_date,
                          WritingSession.ended_at.isnot(None))
                   .all())
                   
        if not sessions:
            return {
                "total_sessions": 0,
                "total_duration": 0,
                "avg_duration": 0,
                "avg_focus_score": 0,
                "session_types": {},
                "completion_rate": 0
            }
            
        # Calculate statistics
        total_sessions = len(sessions)
        session_durations = [(s.ended_at - s.started_at).total_seconds() for s in sessions]
        total_duration = sum(session_durations)
        avg_duration = total_duration / total_sessions if total_sessions > 0 else 0
        
        # Count session types
        session_types = {}
        for session in sessions:
            session_types[session.session_type] = session_types.get(session.session_type, 0) + 1
            
        # Calculate average focus score
        focus_scores = [s.focus_score for s in sessions if s.focus_score is not None]
        avg_focus_score = sum(focus_scores) / len(focus_scores) if focus_scores else 0
        
        # Calculate completion rate (sessions with associated logs / total sessions)
        sessions_with_logs = sum(1 for s in sessions if len(s.logs) > 0)
        completion_rate = sessions_with_logs / total_sessions if total_sessions > 0 else 0
        
        return {
            "total_sessions": total_sessions,
            "total_duration": total_duration,
            "avg_duration": avg_duration,
            "avg_focus_score": avg_focus_score,
            "session_types": session_types,
            "completion_rate": completion_rate
        }
        
    def _calculate_focus_score(self, session: WritingSession) -> float:
        """Calculate focus score based on session metrics"""
        if not session.ended_at:
            return 0.0
            
        # Base score starts at 1.0
        score = 1.0
        
        # Deduct for interruptions
        interruption_penalty = 0.1 * session.interruption_count
        score -= min(interruption_penalty, 0.5)  # Cap penalty at 0.5
        
        # Adjust for session duration
        duration = (session.ended_at - session.started_at).total_seconds()
        if duration < 300:  # Less than 5 minutes
            score *= 0.5
        elif duration < 900:  # Less than 15 minutes
            score *= 0.8
            
        # Bonus for longer focused sessions
        if duration >= 1800 and session.interruption_count == 0:  # 30+ minutes, no interruptions
            score *= 1.2
            
        return max(0.0, min(score, 1.0))  # Clamp between 0 and 1

# Create global instance
session_service = SessionService() 