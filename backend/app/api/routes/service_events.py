"""Service event endpoints.

GET  /service-events         — paginated list with filters
GET  /service-events/{id}    — full detail view
GET  /service-events/categories — distinct event categories
GET  /service-events/stats   — aggregate statistics
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.event_models import ServiceEvent
from app.schemas.common import PaginatedResponse
from app.schemas.event_schemas import (
    ServiceEventDetail,
    ServiceEventListItem,
)
from app.schemas.dashboard_schemas import EventStats


router = APIRouter(prefix="/api/service-events", tags=["service-events"])


@router.get("/", response_model=PaginatedResponse[ServiceEventListItem])
def list_events(
    compressor_id: Optional[str] = None,
    event_category: Optional[str] = None,
    maintenance_activity_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    order_status: Optional[str] = None,
    search: Optional[str] = None,
    event_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """When ``event_id`` is set (e.g. deep link from dashboard), return only that event."""

    q = db.query(ServiceEvent)

    if event_id:
        q = q.filter(ServiceEvent.id == event_id)
        total = q.count()
        rows = (
            q.order_by(ServiceEvent.event_date.desc().nullslast(), ServiceEvent.order_number.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return PaginatedResponse(items=rows, total=total, page=page, page_size=page_size)

    if compressor_id:
        q = q.filter(ServiceEvent.compressor_id == compressor_id)
    if event_category:
        q = q.filter(ServiceEvent.event_category == event_category)
    if maintenance_activity_type:
        q = q.filter(ServiceEvent.maintenance_activity_type == maintenance_activity_type)
    if date_from:
        q = q.filter(ServiceEvent.event_date >= date_from)
    if date_to:
        q = q.filter(ServiceEvent.event_date <= date_to)
    if order_status:
        q = q.filter(ServiceEvent.order_status == order_status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                ServiceEvent.technician_notes_raw.ilike(pattern),
                ServiceEvent.order_description.ilike(pattern),
                ServiceEvent.order_number.ilike(pattern),
            )
        )

    total = q.count()
    rows = (
        q.order_by(ServiceEvent.event_date.desc().nullslast(), ServiceEvent.order_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedResponse(items=rows, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    rows = (
        db.query(ServiceEvent.event_category)
        .filter(ServiceEvent.event_category.isnot(None))
        .distinct()
        .order_by(ServiceEvent.event_category)
        .all()
    )
    return [r[0] for r in rows]


@router.get("/stats", response_model=EventStats)
def event_stats(
    compressor_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ServiceEvent)
    if compressor_id:
        q = q.filter(ServiceEvent.compressor_id == compressor_id)

    by_category = {}
    for row in (
        q.with_entities(ServiceEvent.event_category, func.count(ServiceEvent.id))
        .filter(ServiceEvent.event_category.isnot(None))
        .group_by(ServiceEvent.event_category)
        .all()
    ):
        by_category[row[0]] = row[1]

    by_month: dict[str, int] = {}
    from app.core.config import settings
    if settings.DATABASE_URL.startswith("sqlite"):
        month_col = func.strftime("%Y-%m", ServiceEvent.event_date).label("month")
    else:
        month_col = func.to_char(ServiceEvent.event_date, "YYYY-MM").label("month")
    for row in (
        q.with_entities(month_col, func.count(ServiceEvent.id))
        .filter(ServiceEvent.event_date.isnot(None))
        .group_by("month")
        .order_by("month")
        .all()
    ):
        if row[0]:
            by_month[row[0]] = row[1]

    by_activity = {}
    for row in (
        q.with_entities(ServiceEvent.maintenance_activity_type, func.count(ServiceEvent.id))
        .filter(ServiceEvent.maintenance_activity_type.isnot(None))
        .group_by(ServiceEvent.maintenance_activity_type)
        .all()
    ):
        by_activity[row[0]] = row[1]

    total_cost = q.with_entities(func.sum(ServiceEvent.order_cost)).scalar()
    avg_cost = q.with_entities(func.avg(ServiceEvent.order_cost)).scalar()

    return EventStats(
        by_category=by_category,
        by_month=by_month,
        by_activity_type=by_activity,
        total_cost=round(total_cost, 2) if total_cost else None,
        avg_cost=round(avg_cost, 2) if avg_cost else None,
    )


@router.get("/{event_id}", response_model=ServiceEventDetail)
def get_event(event_id: str, db: Session = Depends(get_db)):
    event = (
        db.query(ServiceEvent)
        .options(
            joinedload(ServiceEvent.actions),
            joinedload(ServiceEvent.notes),
            joinedload(ServiceEvent.measurements),
            joinedload(ServiceEvent.compressor),
            joinedload(ServiceEvent.issue_category),
        )
        .filter(ServiceEvent.id == event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Service event not found")
    return event
