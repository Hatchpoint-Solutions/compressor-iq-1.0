"""Dashboard endpoints — aggregated metrics and highlights."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import asc, case, desc, func, nulls_first, nulls_last, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.master_models import Compressor, IssueCategory, Technician
from app.models.event_models import ServiceEvent, ServiceEventAction, ServiceEventNote
from app.schemas.dashboard_schemas import (
    CompressorDropdownItem,
    DashboardServiceEventItem,
    DashboardSummary,
    MachineAttentionItem,
    TopIssueItem,
)


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)):
    total_events = db.query(func.count(ServiceEvent.id)).scalar() or 0
    total_compressors = db.query(func.count(Compressor.id)).scalar() or 0
    total_fleet_run_hours = db.query(func.coalesce(func.sum(Compressor.current_run_hours), 0.0)).scalar() or 0.0

    all_compressors = db.query(Compressor).order_by(Compressor.unit_id).all()
    compressor_items = [
        CompressorDropdownItem(
            id=c.id,
            unit_id=c.unit_id,
            status=c.status,
            current_run_hours=c.current_run_hours,
            equipment_number=c.equipment_number,
            compressor_type=c.compressor_type,
        )
        for c in all_compressors
    ]

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
        total_fleet_run_hours=round(total_fleet_run_hours, 1),
        recent_events_count=recent_count,
        corrective_count=corrective,
        preventive_count=preventive,
        avg_cost=round(avg_cost, 2) if avg_cost else None,
        top_issues=top_issues,
        machines_needing_attention=machines,
        compressors=compressor_items,
    )


def _fleet_event_select():
    """Scalar subqueries and rank columns for fleet event sorting (correlated to ServiceEvent)."""
    primary_tech_sq = (
        select(func.coalesce(Technician.name, ServiceEventAction.technician_name_raw))
        .select_from(ServiceEventAction)
        .outerjoin(Technician, Technician.id == ServiceEventAction.technician_id)
        .where(ServiceEventAction.service_event_id == ServiceEvent.id)
        .order_by(ServiceEventAction.sequence_number.asc())
        .limit(1)
        .correlate(ServiceEvent)
        .scalar_subquery()
    )
    mgr_sq = (
        select(ServiceEventNote.author_name)
        .where(
            ServiceEventNote.service_event_id == ServiceEvent.id,
            ServiceEventNote.note_type == "review_comment",
            ServiceEventNote.author_name.isnot(None),
            ServiceEventNote.author_name != "",
        )
        .order_by(ServiceEventNote.sequence_number.asc())
        .limit(1)
        .correlate(ServiceEvent)
        .scalar_subquery()
    )
    criticality_rank = case(
        (ServiceEvent.event_category == "corrective", 4),
        (ServiceEvent.event_category == "unscheduled_repair", 3),
        (ServiceEvent.event_category == "preventive_maintenance", 2),
        (ServiceEvent.event_category == "preservation", 1),
        else_=0,
    )
    severity_rank = case(
        (IssueCategory.severity_default == "critical", 4),
        (IssueCategory.severity_default == "high", 3),
        (IssueCategory.severity_default == "medium", 2),
        (IssueCategory.severity_default == "low", 1),
        else_=0,
    )
    return primary_tech_sq, mgr_sq, criticality_rank, severity_rank


FleetSortKey = Literal["event_date", "severity", "criticality", "technician", "manager"]
_ALL_FLEET_KEYS: tuple[FleetSortKey, ...] = (
    "event_date",
    "severity",
    "criticality",
    "technician",
    "manager",
)


def _fleet_order_clause(
    key: FleetSortKey,
    descending: bool,
    *,
    primary_tech_sq,
    mgr_sq,
    criticality_rank,
    severity_rank,
):
    if key == "event_date":
        return (
            desc(ServiceEvent.event_date).nulls_last()
            if descending
            else asc(ServiceEvent.event_date).nulls_first()
        )
    if key == "severity":
        return desc(severity_rank) if descending else asc(severity_rank)
    if key == "criticality":
        return desc(criticality_rank) if descending else asc(criticality_rank)
    if key == "technician":
        return (
            desc(primary_tech_sq).nulls_last()
            if descending
            else asc(primary_tech_sq).nulls_last()
        )
    return desc(mgr_sq).nulls_last() if descending else asc(mgr_sq).nulls_last()


def _resolve_secondary_key(
    primary: FleetSortKey,
    requested: Optional[FleetSortKey],
) -> FleetSortKey:
    """Use ``requested`` when distinct from primary; otherwise first key in fixed order that differs."""
    if requested is not None and requested != primary and requested in _ALL_FLEET_KEYS:
        return requested
    for k in _ALL_FLEET_KEYS:
        if k != primary:
            return k
    return "event_date"


@router.get("/recent-events", response_model=list[DashboardServiceEventItem])
def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
    sort_by: FleetSortKey = "event_date",
    order: Literal["asc", "desc"] = "desc",
    secondary_sort_by: Optional[FleetSortKey] = Query(
        None,
        description="Second sort column (must differ from sort_by; otherwise ignored and auto-picked).",
    ),
    secondary_order: Literal["asc", "desc"] = Query(
        "desc",
        description="Order for the secondary sort column.",
    ),
    db: Session = Depends(get_db),
):
    primary_tech_sq, mgr_sq, criticality_rank, severity_rank = _fleet_event_select()
    order_desc = order == "desc"
    secondary_key = _resolve_secondary_key(sort_by, secondary_sort_by)
    secondary_desc = secondary_order == "desc"

    kw = dict(
        primary_tech_sq=primary_tech_sq,
        mgr_sq=mgr_sq,
        criticality_rank=criticality_rank,
        severity_rank=severity_rank,
    )
    primary_order = _fleet_order_clause(sort_by, order_desc, **kw)
    secondary_order_expr = _fleet_order_clause(secondary_key, secondary_desc, **kw)

    stmt = (
        select(
            ServiceEvent,
            IssueCategory.severity_default.label("issue_severity"),
            criticality_rank.label("crit_r"),
            severity_rank.label("sev_r"),
            primary_tech_sq.label("primary_technician_name"),
            mgr_sq.label("manager_name"),
        )
        .outerjoin(IssueCategory, ServiceEvent.issue_category_id == IssueCategory.id)
        .order_by(
            primary_order,
            secondary_order_expr,
            desc(ServiceEvent.created_at),
            desc(ServiceEvent.order_number),
        )
        .limit(limit)
    )

    rows = db.execute(stmt).all()
    out: list[DashboardServiceEventItem] = []
    for row in rows:
        ev: ServiceEvent = row[0]
        issue_severity = row.issue_severity
        crit_val = row.crit_r
        primary_technician_name = row.primary_technician_name
        manager_name = row.manager_name
        base = DashboardServiceEventItem.model_validate(ev)
        out.append(
            base.model_copy(
                update={
                    "issue_severity": issue_severity,
                    "criticality_rank": int(crit_val or 0),
                    "primary_technician_name": primary_technician_name,
                    "manager_name": manager_name,
                }
            )
        )
    return out


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
