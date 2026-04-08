"""Work orders — assignable corrective work linked to compressors and technicians."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class WorkOrder(Base):
    """A dispatchable unit of work: predictive, system-generated, or ad hoc."""

    __tablename__ = "work_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    compressor_id: Mapped[str] = mapped_column(
        ForeignKey("compressors.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    # predictive | ad_hoc | system
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ad_hoc")
    # open | in_progress | completed | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")

    assigned_technician_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("technicians.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True, index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    compressor: Mapped["Compressor"] = relationship(
        "Compressor", back_populates="work_orders",
    )
    assigned_technician: Mapped[Optional["Technician"]] = relationship(
        "Technician", back_populates="work_orders",
    )
    recommendation: Mapped[Optional["Recommendation"]] = relationship(
        "Recommendation", back_populates="work_orders",
    )
    health_alert_key: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True,
        comment="Dedupe key for system-generated health alerts",
    )

    steps: Mapped[list["WorkOrderStep"]] = relationship(
        back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderStep.step_number",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="work_order",
    )


class WorkOrderStep(Base):
    """Step-by-step instructions for a work order (snapshot at creation time)."""

    __tablename__ = "work_order_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    work_order_id: Mapped[str] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_evidence: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_completed: Mapped[bool] = mapped_column(default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    work_order: Mapped["WorkOrder"] = relationship(back_populates="steps")
