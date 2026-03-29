"""Feedback capture endpoints for technician outcome reporting.

Captures actual outcomes after a recommendation is acted upon,
enabling future learning and resolution rate computation.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.analytics_models import FeedbackOutcome
from app.models.event_models import ServiceEvent
from app.schemas.recommendation_schemas import (
    FeedbackCreateRequest,
    FeedbackResponse,
)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post("/", response_model=FeedbackResponse)
def submit_feedback(body: FeedbackCreateRequest, db: Session = Depends(get_db)):
    """Submit technician feedback for a service event."""
    event = db.query(ServiceEvent).filter(ServiceEvent.id == body.service_event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Service event not found")

    existing = db.query(FeedbackOutcome).filter(
        FeedbackOutcome.service_event_id == body.service_event_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Feedback already exists for this event")

    fb = FeedbackOutcome(
        service_event_id=body.service_event_id,
        recommendation_id=body.recommendation_id,
        actual_action_taken=body.actual_action_taken,
        issue_resolved=body.issue_resolved,
        resolution_notes=body.resolution_notes,
        parts_used=body.parts_used,
        technician_name=body.technician_name,
        feedback_date=date.today(),
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb


@router.get("/event/{event_id}", response_model=FeedbackResponse)
def get_feedback_for_event(event_id: str, db: Session = Depends(get_db)):
    """Get feedback for a specific service event."""
    fb = db.query(FeedbackOutcome).filter(
        FeedbackOutcome.service_event_id == event_id,
    ).first()
    if not fb:
        raise HTTPException(status_code=404, detail="No feedback for this event")
    return fb


@router.get("/", response_model=list[FeedbackResponse])
def list_feedback(db: Session = Depends(get_db)):
    """List all feedback entries (most recent first)."""
    return (
        db.query(FeedbackOutcome)
        .order_by(FeedbackOutcome.created_at.desc())
        .all()
    )
