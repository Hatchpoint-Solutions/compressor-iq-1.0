"""Recommendation and workflow endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import verify_api_key_if_configured
from app.models.analytics_models import Recommendation, WorkflowStep
from app.models.event_models import ServiceEvent
from app.models.master_models import Compressor
from app.schemas.recommendation_schemas import (
    HealthAssessmentResponse,
    RecommendationGenerateRequest,
    RecommendationListItem,
    RecommendationResponse,
    StatusUpdateResponse,
    WorkflowStepResponse,
    WorkflowStepUpdateRequest,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

_MUTATE = [Depends(verify_api_key_if_configured)]


@router.post(
    "/generate/{event_id}",
    response_model=RecommendationResponse,
    dependencies=_MUTATE,
)
def generate_recommendation_for_event(
    event_id: str,
    body: RecommendationGenerateRequest | None = None,
    db: Session = Depends(get_db),
):
    """Generate a recommendation for a specific service event."""
    event = db.query(ServiceEvent).filter(ServiceEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Service event not found")

    from app.services.recommendation_service import generate_recommendation
    rec = generate_recommendation(
        event, db,
        current_description=body.event_description if body else None,
        current_notes=body.technician_notes if body else None,
    )

    return _load_full_recommendation(rec.id, db)


@router.post("/generate", response_model=RecommendationResponse, dependencies=_MUTATE)
def generate_recommendation_general(
    body: RecommendationGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate a recommendation for a machine (no specific event required).

    If machine_id is provided, uses the most recent event for that machine
    as context.
    """
    if not body.machine_id:
        raise HTTPException(
            status_code=400,
            detail="Either machine_id must be provided or use /generate/{event_id}",
        )

    compressor = db.query(Compressor).filter(Compressor.id == body.machine_id).first()
    if not compressor:
        compressor = db.query(Compressor).filter(Compressor.unit_id == body.machine_id).first()
    if not compressor:
        raise HTTPException(status_code=404, detail="Compressor not found")

    from app.services.recommendation_service import generate_recommendation_for_machine
    rec = generate_recommendation_for_machine(
        compressor.id, db,
        description=body.event_description,
        notes=body.technician_notes,
    )

    return _load_full_recommendation(rec.id, db)


@router.get("/", response_model=list[RecommendationListItem])
def list_all_recommendations(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all recommendations across all machines, most recent first."""
    return (
        db.query(Recommendation)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/machine/{machine_id}", response_model=list[RecommendationListItem])
def get_recommendations_for_machine(
    machine_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get historical recommendations for a machine."""
    compressor = db.query(Compressor).filter(Compressor.id == machine_id).first()
    if not compressor:
        compressor = db.query(Compressor).filter(Compressor.unit_id == machine_id).first()
    if not compressor:
        raise HTTPException(status_code=404, detail="Compressor not found")

    recs = (
        db.query(Recommendation)
        .filter(Recommendation.compressor_id == compressor.id)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
    return recs


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(recommendation_id: str, db: Session = Depends(get_db)):
    """Get a specific recommendation with full detail."""
    rec = _load_full_recommendation(recommendation_id, db)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.put(
    "/{recommendation_id}/status",
    response_model=StatusUpdateResponse,
    dependencies=_MUTATE,
)
def update_status(
    recommendation_id: str,
    status: str = Query(...),
    db: Session = Depends(get_db),
) -> StatusUpdateResponse:
    """Update the status of a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    valid = ("pending", "accepted", "rejected", "completed")
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid}")

    rec.status = status
    db.commit()
    return StatusUpdateResponse(id=rec.id, status=rec.status)


@router.put(
    "/workflow-step/{step_id}",
    response_model=WorkflowStepResponse,
    dependencies=_MUTATE,
)
def update_workflow_step(
    step_id: str,
    body: WorkflowStepUpdateRequest,
    db: Session = Depends(get_db),
):
    """Mark a workflow step as completed or add notes."""
    step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Workflow step not found")

    if body.is_completed is not None:
        step.is_completed = body.is_completed
        step.completed_at = datetime.utcnow() if body.is_completed else None
    if body.notes is not None:
        step.notes = body.notes

    db.commit()
    db.refresh(step)
    return step


@router.post(
    "/assess/{compressor_id}",
    response_model=HealthAssessmentResponse,
    dependencies=_MUTATE,
)
def assess_compressor_health(compressor_id: str, db: Session = Depends(get_db)):
    """Generate a proactive health assessment for a compressor.

    Gathers the latest operational data, maintenance history, and
    recurrence patterns, then uses OpenAI (with rule-based fallback)
    to produce actionable recommendations for the operator.
    """
    compressor = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not compressor:
        compressor = db.query(Compressor).filter(Compressor.unit_id == compressor_id).first()
    if not compressor:
        raise HTTPException(status_code=404, detail="Compressor not found")

    from app.services.health_assessment import generate_health_assessment
    return generate_health_assessment(compressor, db)


def _load_full_recommendation(rec_id: str, db: Session) -> Recommendation | None:
    """Load a recommendation with all relationships eagerly loaded."""
    return (
        db.query(Recommendation)
        .options(
            joinedload(Recommendation.workflow_steps),
            joinedload(Recommendation.similar_cases),
        )
        .filter(Recommendation.id == rec_id)
        .first()
    )
