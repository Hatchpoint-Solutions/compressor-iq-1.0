"""Master / reference data models.

Normalized lookup entities that are populated during ingestion and shared
across all service events.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
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


class Site(Base):
    """Physical site / plant location associated with a customer."""

    __tablename__ = "sites"
    __table_args__ = (
        Index("ix_site_plant_customer", "plant_code", "customer_name", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plant_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_source_names: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="Original customer name variants seen",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(),
    )

    compressors: Mapped[list["Compressor"]] = relationship(back_populates="site")


class Compressor(Base):
    """A compressor asset tracked over its service life."""

    __tablename__ = "compressors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    unit_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True,
        comment="Normalized canonical unit ID (e.g. MC6068)",
    )
    raw_source_unit_ids: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="All original unit ID variants observed",
    )
    equipment_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    compressor_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    current_run_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    first_seen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    site_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("sites.id", ondelete="SET NULL"), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now(),
    )

    site: Mapped[Optional["Site"]] = relationship(back_populates="compressors")
    service_events: Mapped[list["ServiceEvent"]] = relationship(back_populates="compressor")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="compressor")


class Technician(Base):
    """A technician / field worker extracted from service notes."""

    __tablename__ = "technicians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    raw_source_names: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="Original name variants observed",
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, unique=True,
        comment="SAP username extracted from notes (e.g. MBURNETT)",
    )
    first_seen_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    actions: Mapped[list["ServiceEventAction"]] = relationship(back_populates="technician")


class MaintenanceActionType(Base):
    """Controlled vocabulary for maintenance action types.

    Maps free-text action descriptions to standardized codes.
    """

    __tablename__ = "maintenance_action_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True,
        comment="Canonical code like OIL_CHANGE, SPARK_PLUG_REPLACEMENT",
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
        comment="Grouping: lubrication, electrical, mechanical, inspection, etc.",
    )
    source_patterns: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True,
        comment="Free-text patterns that map to this action type",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


class IssueCategory(Base):
    """Issue type classification derived from technician notes."""

    __tablename__ = "issue_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity_default: Mapped[str] = mapped_column(String(20), default="medium")
    detection_keywords: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, comment="Keywords used to auto-detect this category",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    service_events: Mapped[list["ServiceEvent"]] = relationship(back_populates="issue_category")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="issue_category")


class ServiceOutcomeType(Base):
    """Reference table for service outcome classification (future use)."""

    __tablename__ = "service_outcome_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_resolved: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())


# Prevent circular import — these are referenced by string in relationships
from app.models.event_models import ServiceEvent, ServiceEventAction  # noqa: E402, F401
from app.models.analytics_models import Recommendation  # noqa: E402, F401
