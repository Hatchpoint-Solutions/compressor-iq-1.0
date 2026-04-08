"""Create and resolve work orders with stepwise workflows."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.analytics_models import Recommendation, WorkflowStep
from app.models.master_models import Compressor, Technician
from app.models.work_order_models import WorkOrder, WorkOrderStep
from app.services.intelligence.workflow_service import generate_workflow

VALID_SOURCES = frozenset({"predictive", "ad_hoc", "system"})
VALID_STATUS = frozenset({"open", "in_progress", "completed", "cancelled"})


def _resolve_compressor(db: Session, compressor_id: str) -> Compressor | None:
    c = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if c:
        return c
    return db.query(Compressor).filter(Compressor.unit_id == compressor_id).first()


def create_work_order(
    db: Session,
    *,
    compressor_id: str,
    title: str,
    source: str,
    description: str | None = None,
    recommendation_id: str | None = None,
    issue_category: str | None = None,
    assigned_technician_id: str | None = None,
    health_alert_key: str | None = None,
) -> WorkOrder:
    if source not in VALID_SOURCES:
        raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
    comp = _resolve_compressor(db, compressor_id)
    if not comp:
        raise ValueError("Compressor not found")

    if assigned_technician_id:
        tech = db.query(Technician).filter(Technician.id == assigned_technician_id).first()
        if not tech:
            raise ValueError("Technician not found")

    rec: Recommendation | None = None
    if recommendation_id:
        rec = db.query(Recommendation).filter(Recommendation.id == recommendation_id).first()
        if not rec:
            raise ValueError("Recommendation not found")
        if rec.compressor_id != comp.id:
            raise ValueError("Recommendation does not belong to this compressor")

    wo = WorkOrder(
        title=title.strip(),
        description=description.strip() if description else None,
        compressor_id=comp.id,
        source=source,
        status="open",
        assigned_technician_id=assigned_technician_id,
        recommendation_id=rec.id if rec else None,
        health_alert_key=health_alert_key,
    )
    db.add(wo)
    db.flush()

    if rec:
        wss = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.recommendation_id == rec.id)
            .order_by(WorkflowStep.step_number)
            .all()
        )
        if wss:
            for ws in wss:
                db.add(
                    WorkOrderStep(
                        work_order_id=wo.id,
                        step_number=ws.step_number,
                        instruction=ws.instruction,
                        rationale=ws.rationale,
                        required_evidence=ws.required_evidence,
                    )
                )
        else:
            cat = rec.likely_issue_category or "general"
            gw = generate_workflow(
                cat,
                has_recurrence=bool(rec.recurrence_signals),
                confidence_label=rec.confidence_label or "medium",
                additional_context=rec.recommended_action,
            )
            for st in gw.steps:
                db.add(
                    WorkOrderStep(
                        work_order_id=wo.id,
                        step_number=st.step_number,
                        instruction=st.instruction,
                        rationale=st.rationale,
                        required_evidence=st.required_evidence,
                    )
                )
    else:
        cat = (issue_category or "general").strip() or "general"
        gw = generate_workflow(cat, has_recurrence=False, confidence_label="medium")
        for st in gw.steps:
            db.add(
                WorkOrderStep(
                    work_order_id=wo.id,
                    step_number=st.step_number,
                    instruction=st.instruction,
                    rationale=st.rationale,
                    required_evidence=st.required_evidence,
                )
            )

    db.commit()
    db.refresh(wo)

    if assigned_technician_id:
        tech = db.query(Technician).filter(Technician.id == assigned_technician_id).first()
        if tech:
            from app.services.notification_service import notify_work_order_assigned

            notify_work_order_assigned(db, work_order=wo, technician=tech, unit_id=comp.unit_id)

    return wo


def create_work_orders_from_health_alerts(
    db: Session,
    compressor: Compressor,
    alerts: list,
) -> list[str]:
    """Open system work orders for severe health alerts (deduped by health_alert_key)."""
    if not settings.AUTO_WORK_ORDERS_FROM_HEALTH_ALERTS:
        return []

    allowed = settings.health_alert_work_order_severity_set
    created: list[str] = []
    from app.services.notification_service import notify_system_work_order

    for a in alerts:
        sev = getattr(a, "severity", "medium").lower()
        if sev not in allowed:
            continue
        title = getattr(a, "title", "Health alert") or "Health alert"
        desc = getattr(a, "description", "") or ""
        rec_action = getattr(a, "recommended_action", "") or ""
        fp = hashlib.sha256(f"{compressor.id}|{title.strip().lower()}".encode()).hexdigest()[:32]
        dup = (
            db.query(WorkOrder)
            .filter(
                WorkOrder.compressor_id == compressor.id,
                WorkOrder.health_alert_key == fp,
                WorkOrder.status.in_(("open", "in_progress")),
            )
            .first()
        )
        if dup:
            continue
        body = "\n\n".join(p for p in (desc, rec_action) if p)
        try:
            wo = create_work_order(
                db,
                compressor_id=compressor.id,
                title=f"[Health] {title}"[:300],
                source="system",
                description=body[:8000] if body else None,
                issue_category=_issue_category_from_alert_title(title),
                health_alert_key=fp,
            )
            created.append(wo.id)
            notify_system_work_order(db, compressor=compressor, work_order=wo, alert_title=title)
        except ValueError:
            continue
    return created


def _issue_category_from_alert_title(title: str) -> str:
    """Map common health alert titles to workflow template keys when possible."""
    t = title.lower()
    if "detonation" in t:
        return "detonation"
    return "general"


def list_work_orders(
    db: Session,
    *,
    status: str | None = None,
    compressor_id: str | None = None,
    assigned_technician_id: str | None = None,
    limit: int = 100,
) -> list[WorkOrder]:
    q = db.query(WorkOrder).options(
        joinedload(WorkOrder.compressor),
        joinedload(WorkOrder.assigned_technician),
    )
    if status:
        q = q.filter(WorkOrder.status == status)
    if compressor_id:
        c = _resolve_compressor(db, compressor_id)
        if c:
            q = q.filter(WorkOrder.compressor_id == c.id)
        else:
            return []
    if assigned_technician_id:
        q = q.filter(WorkOrder.assigned_technician_id == assigned_technician_id)
    return (
        q.order_by(WorkOrder.created_at.desc())
        .limit(limit)
        .all()
    )


def get_work_order(db: Session, work_order_id: str) -> WorkOrder | None:
    return (
        db.query(WorkOrder)
        .options(
            joinedload(WorkOrder.compressor),
            joinedload(WorkOrder.assigned_technician),
            joinedload(WorkOrder.steps),
        )
        .filter(WorkOrder.id == work_order_id)
        .first()
    )


def update_work_order(
    db: Session,
    work_order_id: str,
    *,
    status: str | None = None,
    assigned_technician_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
    unset_assignee: bool = False,
) -> WorkOrder | None:
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if not wo:
        return None
    previous_assignee = wo.assigned_technician_id
    if status is not None:
        if status not in VALID_STATUS:
            raise ValueError(f"status must be one of {sorted(VALID_STATUS)}")
        wo.status = status
        if status == "completed":
            wo.completed_at = datetime.now(timezone.utc)
        elif status in ("open", "in_progress", "cancelled"):
            wo.completed_at = None
    if unset_assignee:
        wo.assigned_technician_id = None
    elif assigned_technician_id is not None:
        if assigned_technician_id:
            tech = db.query(Technician).filter(Technician.id == assigned_technician_id).first()
            if not tech:
                raise ValueError("Technician not found")
        wo.assigned_technician_id = assigned_technician_id or None
    if title is not None:
        wo.title = title.strip()
    if description is not None:
        wo.description = description.strip() if description else None
    db.commit()
    db.refresh(wo)

    new_assignee = wo.assigned_technician_id
    if new_assignee and new_assignee != previous_assignee:
        tech = db.query(Technician).filter(Technician.id == new_assignee).first()
        comp = db.query(Compressor).filter(Compressor.id == wo.compressor_id).first()
        if tech and comp:
            from app.services.notification_service import notify_work_order_assigned

            notify_work_order_assigned(
                db, work_order=wo, technician=tech, unit_id=comp.unit_id,
            )

    return wo


def update_work_order_step(
    db: Session,
    work_order_id: str,
    step_id: str,
    *,
    is_completed: bool | None = None,
    notes: str | None = None,
) -> WorkOrderStep | None:
    step = (
        db.query(WorkOrderStep)
        .filter(WorkOrderStep.id == step_id, WorkOrderStep.work_order_id == work_order_id)
        .first()
    )
    if not step:
        return None
    if is_completed is not None:
        step.is_completed = is_completed
        step.completed_at = datetime.now(timezone.utc) if is_completed else None
    if notes is not None:
        step.notes = notes
    wo = db.query(WorkOrder).filter(WorkOrder.id == work_order_id).first()
    if wo and wo.status == "open" and (is_completed is True or step.is_completed):
        wo.status = "in_progress"
    db.commit()
    db.refresh(step)
    return step
