"""In-app notifications for fleet events and technician assignments."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Notification(Base):
    """A user-visible notification (fleet-wide or targeted to one technician)."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # system_work_order | work_order_assigned | ...
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    compressor_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("compressors.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    work_order_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("work_orders.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    # NULL = visible to everyone (e.g. system-created WO); else only that technician
    technician_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("technicians.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    work_order: Mapped[Optional["WorkOrder"]] = relationship(
        "WorkOrder", back_populates="notifications",
    )
