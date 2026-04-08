"""Create and query in-app notifications."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.master_models import Compressor, Technician
from app.models.notification_models import Notification
from app.models.work_order_models import WorkOrder


def create_notification(
    db: Session,
    *,
    category: str,
    title: str,
    body: str | None = None,
    compressor_id: str | None = None,
    work_order_id: str | None = None,
    technician_id: str | None = None,
) -> Notification:
    n = Notification(
        category=category,
        title=title,
        body=body,
        compressor_id=compressor_id,
        work_order_id=work_order_id,
        technician_id=technician_id,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def notify_system_work_order(
    db: Session,
    *,
    compressor: Compressor,
    work_order: WorkOrder,
    alert_title: str,
) -> None:
    """Fleet-visible notification when the system opens a work order from health data."""
    create_notification(
        db,
        category="system_work_order",
        title=f"System work order: {compressor.unit_id}",
        body=f"{alert_title}\n\n{work_order.title}",
        compressor_id=compressor.id,
        work_order_id=work_order.id,
        technician_id=None,
    )


def notify_work_order_assigned(
    db: Session,
    *,
    work_order: WorkOrder,
    technician: Technician,
    unit_id: str,
) -> None:
    create_notification(
        db,
        category="work_order_assigned",
        title=f"Assigned: {work_order.title}",
        body=f"Unit {unit_id} — open My work to complete steps.",
        compressor_id=work_order.compressor_id,
        work_order_id=work_order.id,
        technician_id=technician.id,
    )


def list_notifications(
    db: Session,
    *,
    technician_id: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
) -> list[Notification]:
    q = db.query(Notification)
    if technician_id:
        q = q.filter(
            (Notification.technician_id.is_(None))
            | (Notification.technician_id == technician_id),
        )
    if unread_only:
        q = q.filter(Notification.read_at.is_(None))
    return q.order_by(Notification.created_at.desc()).limit(limit).all()


def mark_read(db: Session, notification_id: str) -> Notification | None:
    from datetime import datetime, timezone

    n = db.query(Notification).filter(Notification.id == notification_id).first()
    if not n:
        return None
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(n)
    return n


def mark_all_read_for_viewer(db: Session, technician_id: str | None) -> int:
    from datetime import datetime, timezone

    q = db.query(Notification).filter(Notification.read_at.is_(None))
    if technician_id:
        q = q.filter(
            (Notification.technician_id.is_(None))
            | (Notification.technician_id == technician_id),
        )
    rows = q.all()
    now = datetime.now(timezone.utc)
    for n in rows:
        n.read_at = now
    db.commit()
    return len(rows)
