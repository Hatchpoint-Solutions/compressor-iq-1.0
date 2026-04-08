"""In-app notifications."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import verify_api_key_if_configured
from app.schemas.notification_schemas import (
    MarkAllReadResponse,
    MarkReadResponse,
    NotificationResponse,
)
from app.services import notification_service as notif_svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/", response_model=list[NotificationResponse])
def list_notifications(
    technician_id: str | None = Query(
        None,
        description="When set, include fleet-wide (unassigned) plus this technician's items",
    ),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = notif_svc.list_notifications(
        db,
        technician_id=technician_id,
        unread_only=unread_only,
        limit=limit,
    )
    return [NotificationResponse.model_validate(r) for r in rows]


@router.patch(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    dependencies=[Depends(verify_api_key_if_configured)],
)
def mark_one_read(notification_id: str, db: Session = Depends(get_db)):
    n = notif_svc.mark_read(db, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    return MarkReadResponse(id=n.id, read_at=n.read_at)


@router.post(
    "/mark-all-read",
    response_model=MarkAllReadResponse,
    dependencies=[Depends(verify_api_key_if_configured)],
)
def mark_all_read(
    technician_id: str | None = Query(None),
    db: Session = Depends(get_db),
):
    count = notif_svc.mark_all_read_for_viewer(db, technician_id)
    return MarkAllReadResponse(marked_count=count)
