"""Dashboard endpoints — aggregated metrics and highlights."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.master_models import Compressor
from app.models.event_models import ServiceEvent
from app.schemas.dashboard_schemas import (
    DashboardSummary,
    MachineAttentionItem,
    TopIssueItem,
)
from app.schemas.event_schemas import ServiceEventListItem


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    total_events = db.query(func.count(ServiceEvent.id)).scalar() or 0
    total_compressors = db.query(func.count(Compressor.id)).scalar() or 0

    thirty_days_ago = date.today() - timedelta(days=30)
    recent_count = (
        db.query(func.count(ServiceEvent.id))
        .filter(ServiceEvent.event_date >= thirty_days_ago)
        .scalar() or 0
    )
    corrective = (
        db.query(func.count(ServiceEvent.id))
        .filter(ServiceEvent.event_category == "corrective")
        .scalar() or 0
    )
    preventive = (
        db.query(func.count(ServiceEvent.id))
        .filter(ServiceEvent.event_category == "preventive_maintenance")
        .scalar() or 0
    )
    avg_cost = db.query(func.avg(ServiceEvent.order_cost)).scalar()

    cat_rows = (
        db.query(ServiceEvent.event_category, func.count(ServiceEvent.id).label("cnt"))
        .filter(ServiceEvent.event_category.isnot(None))
        .group_by(ServiceEvent.event_category)
        .order_by(func.count(ServiceEvent.id).desc())
        .limit(10)
        .all()
    )
    top_issues = [
        TopIssueItem(
            category=row[0],
            count=row[1],
            percentage=round(row[1] / total_events * 100, 1) if total_events else 0,
        )
        for row in cat_rows
    ]

    attention_rows = (
        db.query(
            Compressor.id,
            Compressor.unit_id,
            func.count(ServiceEvent.id).label("cnt"),
            func.max(ServiceEvent.event_date).label("last_date"),
        )
        .join(ServiceEvent, ServiceEvent.compressor_id == Compressor.id)
        .filter(
            ServiceEvent.event_category == "corrective",
            ServiceEvent.event_date >= thirty_days_ago,
        )
        .group_by(Compressor.id, Compressor.unit_id)
        .having(func.count(ServiceEvent.id) >= 1)
        .order_by(func.count(ServiceEvent.id).desc())
        .limit(10)
        .all()
    )
    machines = [
        MachineAttentionItem(
            compressor_id=r[0],
            unit_id=r[1],
            recent_event_count=r[2],
            last_event_category="corrective",
            last_event_date=r[3],
        )
        for r in attention_rows
    ]

    return DashboardSummary(
        total_events=total_events,
        total_compressors=total_compressors,
        recent_events_count=recent_count,
        corrective_count=corrective,
        preventive_count=preventive,
        avg_cost=round(avg_cost, 2) if avg_cost else None,
        top_issues=top_issues,
        machines_needing_attention=machines,
    )


@router.get("/recent-events", response_model=list[ServiceEventListItem])
def get_recent_events(limit: int = 10, db: Session = Depends(get_db)):
    return (
        db.query(ServiceEvent)
        .order_by(ServiceEvent.event_date.desc().nullslast(), ServiceEvent.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/recurring-issues", response_model=list[TopIssueItem])
def get_recurring_issues(db: Session = Depends(get_db)):
    total = db.query(func.count(ServiceEvent.id)).scalar() or 1
    rows = (
        db.query(ServiceEvent.event_category, func.count(ServiceEvent.id).label("cnt"))
        .filter(ServiceEvent.event_category.isnot(None))
        .group_by(ServiceEvent.event_category)
        .order_by(func.count(ServiceEvent.id).desc())
        .limit(10)
        .all()
    )
    return [
        TopIssueItem(category=r[0], count=r[1], percentage=round(r[1] / total * 100, 1))
        for r in rows
    ]
