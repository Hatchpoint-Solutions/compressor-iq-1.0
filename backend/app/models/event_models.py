"""Core service event models.

These represent the normalized business entities produced by the ingestion
pipeline.  Every record traces back to its source via ``import_batch_id``,
``import_file_id``, and ``raw_row_id``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ServiceEvent(Base):
    """A single maintenance work order / service event."""

    __tablename__ = "service_events"
    __table_args__ = (
        Index("ix_event_compressor_date", "compressor_id", "event_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    compressor_id: Mapped[str] = mapped_column(
        ForeignKey("compressors.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
    )
    order_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_order_and_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Original compound 'Order & Description' value",
    )

    event_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    event_date_source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="reading_date | estimated_from_description | estimated_from_notes",
    )
    event_date_estimated: Mapped[bool] = mapped_column(Boolean, default=False)

    event_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    maintenance_activity_type_raw: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="Original value from spreadsheet",
    )
    maintenance_activity_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Normalized: unscheduled_repair, preventive_maintenance, preservation",
    )

    order_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    order_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    user_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    technician_notes_raw: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Original technician notes verbatim",
    )
    technician_notes_clean: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Cleaned version for analytics",
    )

    run_hours_at_event: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    order_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    order_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")

    plant_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    issue_category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("issue_categories.id", ondelete="SET NULL"), nullable=True,
    )

    # Lineage / traceability
    import_batch_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL"), nullable=True,
    )
    import_file_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("import_files.id", ondelete="SET NULL"), nullable=True,
    )
    raw_row_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("raw_service_rows.id", ondelete="SET NULL"), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(),
    )

    # Relationships
    compressor: Mapped["Compressor"] = relationship(back_populates="service_events")
    issue_category: Mapped[Optional["IssueCategory"]] = relationship(back_populates="service_events")
    actions: Mapped[list["ServiceEventAction"]] = relationship(
        back_populates="service_event", cascade="all, delete-orphan",
    )
    notes: Mapped[list["ServiceEventNote"]] = relationship(
        back_populates="service_event", cascade="all, delete-orphan",
    )
    measurements: Mapped[list["ServiceEventMeasurement"]] = relationship(
        back_populates="service_event", cascade="all, delete-orphan",
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="service_event", cascade="all, delete-orphan",
    )
    similar_cases: Mapped[list["SimilarCase"]] = relationship(
        back_populates="service_event", foreign_keys="SimilarCase.service_event_id",
    )
    feedback: Mapped[Optional["FeedbackOutcome"]] = relationship(
        back_populates="service_event", uselist=False,
    )


class ServiceEventAction(Base):
    """Individual maintenance action parsed from technician notes."""

    __tablename__ = "service_event_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_event_id: Mapped[str] = mapped_column(
        ForeignKey("service_events.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    action_type_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("maintenance_action_types.id", ondelete="SET NULL"), nullable=True,
    )
    action_type_raw: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="Original action text before normalization",
    )
    component: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    technician_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("technicians.id", ondelete="SET NULL"), nullable=True,
    )
    technician_name_raw: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="Original name as extracted from notes",
    )

    action_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    run_hours_at_action: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    service_event: Mapped["ServiceEvent"] = relationship(back_populates="actions")
    technician: Mapped[Optional["Technician"]] = relationship(back_populates="actions")


class ServiceEventNote(Base):
    """Structured note entries parsed from the review comments field."""

    __tablename__ = "service_event_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_event_id: Mapped[str] = mapped_column(
        ForeignKey("service_events.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    note_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="technician_note",
        comment="technician_note | review_comment | system_note",
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    note_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)

    service_event: Mapped["ServiceEvent"] = relationship(back_populates="notes")


class ServiceEventMeasurement(Base):
    """Structured numeric measurements extracted from service data."""

    __tablename__ = "service_event_measurements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_event_id: Mapped[str] = mapped_column(
        ForeignKey("service_events.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    measurement_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="run_hours | pressure | temperature | cost",
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="hrs | psi | F | USD")
    measured_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="reading_date | extracted_from_notes",
    )

    service_event: Mapped["ServiceEvent"] = relationship(back_populates="measurements")


# Resolve forward references
from app.models.master_models import Compressor, IssueCategory, Technician  # noqa: E402, F401
from app.models.analytics_models import FeedbackOutcome, Recommendation, SimilarCase  # noqa: E402, F401
