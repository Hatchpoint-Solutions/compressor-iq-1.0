"""Fleet maintenance cost, preventive vs corrective, and aging-style time series."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event_models import ServiceEvent
from app.models.master_models import Compressor, Site
from app.schemas.fleet_analytics_schemas import (
    AnalyticsEntityOption,
    CompareEntityMetrics,
    CostPeriodPoint,
    FleetAgingPoint,
    FleetMaintenanceOverview,
    FleetRunHoursSnapshot,
)


def _is_sqlite() -> bool:
    return settings.DATABASE_URL.startswith("sqlite")


def _period_column(granularity: Literal["month", "year"]):
    col = ServiceEvent.event_date
    if _is_sqlite():
        if granularity == "month":
            return func.strftime("%Y-%m", col).label("period")
        return func.strftime("%Y", col).label("period")
    if granularity == "month":
        return func.to_char(col, "YYYY-MM").label("period")
    return func.to_char(col, "YYYY").label("period")


def _default_date_range() -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=365)
    return start, end


def build_fleet_overview(
    db: Session,
    date_from: date | None,
    date_to: date | None,
    granularity: Literal["month", "year"],
) -> FleetMaintenanceOverview:
    start, end = date_from, date_to
    if end is None or start is None:
        start, end = _default_date_range()
    if start > end:
        start, end = end, start

    period_col = _period_column(granularity)
    date_flt = (
        ServiceEvent.event_date.isnot(None),
        ServiceEvent.event_date >= start,
        ServiceEvent.event_date <= end,
    )

    cost_rows = (
        db.query(ServiceEvent)
        .filter(*date_flt)
        .with_entities(
            period_col,
            func.coalesce(func.sum(ServiceEvent.order_cost), 0.0),
            func.count(ServiceEvent.id),
        )
        .group_by("period")
        .order_by("period")
        .all()
    )
    cost_series = [
        CostPeriodPoint(period=r[0], total_cost=float(r[1] or 0), event_count=int(r[2] or 0))
        for r in cost_rows
        if r[0]
    ]

    corr_cost = float(
        db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0))
        .filter(*date_flt, ServiceEvent.event_category == "corrective")
        .scalar()
        or 0
    )
    corr_n = int(
        db.query(func.count(ServiceEvent.id))
        .filter(*date_flt, ServiceEvent.event_category == "corrective")
        .scalar()
        or 0
    )
    prev_cost = float(
        db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0))
        .filter(*date_flt, ServiceEvent.event_category == "preventive_maintenance")
        .scalar()
        or 0
    )
    prev_n = int(
        db.query(func.count(ServiceEvent.id))
        .filter(*date_flt, ServiceEvent.event_category == "preventive_maintenance")
        .scalar()
        or 0
    )
    q_other = db.query(ServiceEvent).filter(*date_flt).filter(
        (ServiceEvent.event_category.is_(None))
        | (
            (ServiceEvent.event_category != "corrective")
            & (ServiceEvent.event_category != "preventive_maintenance")
        )
    )
    other_cost = float(
        q_other.with_entities(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0)).scalar() or 0
    )
    other_n = int(q_other.with_entities(func.count(ServiceEvent.id)).scalar() or 0)

    total_maint = corr_cost + prev_cost + other_cost

    aging_base = db.query(ServiceEvent).filter(
        ServiceEvent.event_date.isnot(None),
        ServiceEvent.event_date >= start,
        ServiceEvent.event_date <= end,
        ServiceEvent.run_hours_at_event.isnot(None),
    )
    aging_rows = (
        aging_base.with_entities(
            period_col,
            func.avg(ServiceEvent.run_hours_at_event),
            func.count(ServiceEvent.id),
        )
        .group_by("period")
        .order_by("period")
        .all()
    )
    fleet_aging_series = [
        FleetAgingPoint(
            period=r[0],
            avg_run_hours_at_service=round(float(r[1]), 1) if r[1] is not None else None,
            events_with_run_hours=int(r[2] or 0),
        )
        for r in aging_rows
        if r[0]
    ]

    comps = db.query(Compressor).all()
    hours = [c.current_run_hours for c in comps if c.current_run_hours is not None]
    ages_y: list[float] = []
    today = date.today()
    for c in comps:
        if c.first_seen_date is not None:
            ages_y.append((today - c.first_seen_date).days / 365.25)

    median_h: float | None = None
    if hours:
        srt = sorted(hours)
        mid = len(srt) // 2
        median_h = float(srt[mid]) if len(srt) % 2 else (srt[mid - 1] + srt[mid]) / 2.0

    snapshot = FleetRunHoursSnapshot(
        compressor_count=len(comps),
        avg_current_run_hours=round(sum(hours) / len(hours), 1) if hours else None,
        median_current_run_hours=round(median_h, 1) if median_h is not None else None,
        avg_age_years=round(sum(ages_y) / len(ages_y), 1) if ages_y else None,
    )

    return FleetMaintenanceOverview(
        granularity=granularity,
        date_from=start,
        date_to=end,
        cost_series=cost_series,
        total_maintenance_cost=round(total_maint, 2),
        corrective_cost=round(corr_cost, 2),
        preventive_cost=round(prev_cost, 2),
        other_cost=round(other_cost, 2),
        corrective_event_count=corr_n,
        preventive_event_count=prev_n,
        other_event_count=other_n,
        fleet_aging_series=fleet_aging_series,
        fleet_run_hours_snapshot=snapshot,
    )


def list_entity_options(db: Session, kind: Literal["compressor", "site"]) -> list[AnalyticsEntityOption]:
    if kind == "compressor":
        rows = db.query(Compressor).order_by(Compressor.unit_id).all()
        return [AnalyticsEntityOption(id=c.id, label=c.unit_id) for c in rows]
    rows = (
        db.query(Site.id, Site.plant_code, Site.customer_name)
        .join(Compressor, Compressor.site_id == Site.id)
        .group_by(Site.id, Site.plant_code, Site.customer_name)
        .order_by(Site.plant_code, Site.customer_name)
        .all()
    )
    out: list[AnalyticsEntityOption] = []
    for sid, plant, cust in rows:
        label = f"{plant} · {cust}" if plant and cust else (plant or cust or sid)
        out.append(AnalyticsEntityOption(id=sid, label=label))
    return out


def compare_entities(
    db: Session,
    entity_type: Literal["compressor", "site"],
    entity_ids: list[str],
    date_from: date,
    date_to: date,
) -> list[CompareEntityMetrics]:
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    results: list[CompareEntityMetrics] = []

    for eid in entity_ids:
        if entity_type == "compressor":
            comp = db.query(Compressor).filter(Compressor.id == eid).first()
            if not comp:
                continue
            label = comp.unit_id

            def _flt():
                return (
                    ServiceEvent.compressor_id == eid,
                    ServiceEvent.event_date.isnot(None),
                    ServiceEvent.event_date >= date_from,
                    ServiceEvent.event_date <= date_to,
                )
        else:
            site = db.query(Site).filter(Site.id == eid).first()
            if not site:
                continue
            label = f"{site.plant_code} · {site.customer_name}"

            def _flt():
                return (
                    Compressor.site_id == eid,
                    ServiceEvent.event_date.isnot(None),
                    ServiceEvent.event_date >= date_from,
                    ServiceEvent.event_date <= date_to,
                )

        if entity_type == "compressor":
            total_cost = float(
                db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0)).filter(*_flt()).scalar() or 0
            )
            event_count = int(db.query(func.count(ServiceEvent.id)).filter(*_flt()).scalar() or 0)
            corr = db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0)).filter(
                *_flt(),
                ServiceEvent.event_category == "corrective",
            ).scalar()
            prev = db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0)).filter(
                *_flt(),
                ServiceEvent.event_category == "preventive_maintenance",
            ).scalar()
            avg_order = db.query(func.avg(ServiceEvent.order_cost)).filter(*_flt()).scalar()
            avg_rh = db.query(func.avg(ServiceEvent.run_hours_at_event)).filter(*_flt()).scalar()
        else:
            total_cost = float(
                db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0))
                .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
                .filter(*_flt())
                .scalar()
                or 0
            )
            event_count = int(
                db.query(func.count(ServiceEvent.id))
                .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
                .filter(*_flt())
                .scalar()
                or 0
            )
            corr = (
                db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0))
                .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
                .filter(
                    *_flt(),
                    ServiceEvent.event_category == "corrective",
                )
                .scalar()
            )
            prev = (
                db.query(func.coalesce(func.sum(ServiceEvent.order_cost), 0.0))
                .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
                .filter(
                    *_flt(),
                    ServiceEvent.event_category == "preventive_maintenance",
                )
                .scalar()
            )
            avg_order = (
                db.query(func.avg(ServiceEvent.order_cost))
                .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
                .filter(*_flt())
                .scalar()
            )
            avg_rh = (
                db.query(func.avg(ServiceEvent.run_hours_at_event))
                .join(Compressor, ServiceEvent.compressor_id == Compressor.id)
                .filter(*_flt())
                .scalar()
            )

        other_cost = total_cost - float(corr or 0) - float(prev or 0)

        results.append(
            CompareEntityMetrics(
                entity_id=eid,
                label=label,
                total_cost=round(total_cost, 2),
                event_count=event_count,
                corrective_cost=round(float(corr or 0), 2),
                preventive_cost=round(float(prev or 0), 2),
                other_cost=round(max(other_cost, 0.0), 2),
                avg_order_cost=round(float(avg_order), 2) if avg_order is not None else None,
                avg_run_hours_at_event=round(float(avg_rh), 1) if avg_rh is not None else None,
            )
        )

    return results
