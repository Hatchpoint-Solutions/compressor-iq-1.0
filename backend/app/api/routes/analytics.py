"""Analytics endpoints for descriptive intelligence.

Provides machine-level analytics summaries including action frequencies,
issue frequencies, recurrence signals, and service interval statistics.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.master_models import Compressor
from app.schemas.recommendation_schemas import (
    ActionFrequencyResponse,
    AnalyticsSummaryResponse,
    IssueFrequencyResponse,
    RecurrenceSignalDetailResponse,
)
from app.services.intelligence.analytics_service import build_analytics_summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary/{machine_id}", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(machine_id: str, db: Session = Depends(get_db)):
    """Get a full analytics summary for a machine.

    Includes action frequencies, issue frequencies, recurrence signals,
    and service interval statistics.
    """
    compressor = db.query(Compressor).filter(Compressor.id == machine_id).first()
    if not compressor:
        compressor = db.query(Compressor).filter(Compressor.unit_id == machine_id).first()
    if not compressor:
        raise HTTPException(status_code=404, detail="Compressor not found")

    summary = build_analytics_summary(db, compressor.id)

    return AnalyticsSummaryResponse(
        total_events=summary.total_events,
        action_frequencies=[
            ActionFrequencyResponse(
                action_type=af.action_type,
                count=af.count,
                percentage=af.percentage,
            )
            for af in summary.action_frequencies
        ],
        issue_frequencies=[
            IssueFrequencyResponse(
                category=af.action_type,
                count=af.count,
                percentage=af.percentage,
            )
            for af in summary.issue_frequencies
        ],
        recurrence_signals=[
            RecurrenceSignalDetailResponse(
                signal_type=rs.signal_type,
                description=rs.description,
                event_count=rs.event_count,
                time_span_days=rs.time_span_days,
                severity=rs.severity,
            )
            for rs in summary.recurrence_signals
        ],
        recent_event_count_30d=summary.recent_event_count_30d,
        recent_event_count_90d=summary.recent_event_count_90d,
        avg_days_between_events=summary.avg_days_between_events,
    )
