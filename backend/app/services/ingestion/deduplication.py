"""Stage 7: Deduplication.

Provides functions to detect duplicate rows (by content hash) and duplicate
service events (by order number).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.import_models import RawServiceRow
from app.models.event_models import ServiceEvent


def is_duplicate_raw_row(db: Session, row_hash: str) -> bool:
    """Check whether a row with the same content fingerprint already exists."""
    return (
        db.query(RawServiceRow.id)
        .filter(RawServiceRow.row_hash == row_hash)
        .first()
    ) is not None


def is_duplicate_order_number(db: Session, order_number: str) -> bool:
    """Check whether a service event with this order number already exists."""
    return (
        db.query(ServiceEvent.id)
        .filter(ServiceEvent.order_number == order_number)
        .first()
    ) is not None


def find_existing_event_by_order(db: Session, order_number: str) -> ServiceEvent | None:
    """Return the existing service event for a given order number, if any."""
    return (
        db.query(ServiceEvent)
        .filter(ServiceEvent.order_number == order_number)
        .first()
    )
