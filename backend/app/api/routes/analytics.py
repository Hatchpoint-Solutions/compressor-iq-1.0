"""Analytics endpoints for descriptive intelligence.

Provides machine-level analytics summaries including action frequencies,
issue frequencies, recurrence signals, and service interval statistics.
Fleet-level endpoints cover maintenance cost trends, preventive vs corrective
split, fleet aging proxies, and multi-entity comparison.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.master_models import Compressor
from app.schemas.fleet_analytics_schemas import (
    AnalyticsEntityOption,
    FleetCompareResponse,
    FleetMaintenanceOverview,
)
from app.schemas.recommendation_schemas import (
    ActionFrequencyResponse,
    AnalyticsSummaryResponse,
    IssueFrequencyResponse,
    RecurrenceSignalDetailResponse,
)
from app.services.fleet_analytics_service import (
    build_fleet_overview,
    compare_entities,
    list_entity_options,
)
from app.services.intelligence.analytics_service import build_analytics_summary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Comparison charts stay readable; adjust if product needs a different cap.
FLEET_COMPARE_MIN_ENTITIES = 2
FLEET_COMPARE_MAX_ENTITIES = 12


@router.get("/fleet/overview", response_model=FleetMaintenanceOverview)
def fleet_overview(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    granularity: Literal["month", "year"] = Query("month"),
    db: Session = Depends(get_db),
):
    """Fleet maintenance cost by period, corrective vs preventive cost, and aging-style series."""
    return build_fleet_overview(db, date_from, date_to, granularity)


@router.get("/fleet/entities", response_model=list[AnalyticsEntityOption])
def fleet_entities(
    kind: Literal["compressor", "site"] = Query("compressor"),
    db: Session = Depends(get_db),
):
    """Compressors or sites (with at least one compressor) for comparison pickers."""
    return list_entity_options(db, kind)


@router.get("/fleet/compare", response_model=FleetCompareResponse)
def fleet_compare(
    entity_type: Literal["compressor", "site"] = Query(...),
    entity_ids: list[str] = Query(...),
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    """Compare maintenance cost and workload for multiple compressors or sites over a date range."""
    unique_ids = list(dict.fromkeys(entity_ids))
    if len(unique_ids) < FLEET_COMPARE_MIN_ENTITIES or len(unique_ids) > FLEET_COMPARE_MAX_ENTITIES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Provide between {FLEET_COMPARE_MIN_ENTITIES} and {FLEET_COMPARE_MAX_ENTITIES} "
                "distinct entity IDs."
            ),
        )
    d0, d1 = date_from, date_to
    if d0 > d1:
        d0, d1 = d1, d0
    rows = compare_entities(db, entity_type, unique_ids, d0, d1)
    if len(rows) != len(unique_ids):
        raise HTTPException(status_code=404, detail="One or more entities were not found.")
    return FleetCompareResponse(
        entity_type=entity_type,
        date_from=d0,
        date_to=d1,
        entities=rows,
    )


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
