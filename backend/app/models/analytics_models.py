"""Analytics / recommendation models.

These support the recommendation engine, workflow steps, similar-case matching
and technician feedback.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_event_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("service_events.id", ondelete="SET NULL"), nullable=True,
    )
    compressor_id: Mapped[str] = mapped_column(
        ForeignKey("compressors.id", ondelete="CASCADE"), nullable=False,
    )
    issue_category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("issue_categories.id", ondelete="SET NULL"), nullable=True,
    )
    likely_issue_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
        comment="Human-readable issue category name",
    )
    recommended_action: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True,
        comment="Primary recommended maintenance action",
    )
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_label: Mapped[str] = mapped_column(
        String(20), default="low",
        comment="high / medium / low",
    )
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_summary: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="Structured evidence: similar_case_count, top_action, resolution_rate, etc.",
    )
    recurrence_signals: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
        comment="Detected recurrence patterns and repeat-event indicators",
    )
    suggested_parts_or_checks: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True,
        comment="Parts or checks inferred from similar cases",
    )
    similar_case_count: Mapped[int] = mapped_column(Integer, default=0)
    most_frequent_action: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    resolution_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fallback_note: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Explanation when confidence is low or evidence is sparse",
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    service_event: Mapped[Optional["ServiceEvent"]] = relationship(back_populates="recommendations")
    compressor: Mapped["Compressor"] = relationship(back_populates="recommendations")
    issue_category: Mapped[Optional["IssueCategory"]] = relationship(back_populates="recommendations")
    workflow_steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan",
        order_by="WorkflowStep.step_number",
    )
    similar_cases: Mapped[list["SimilarCase"]] = relationship(
        back_populates="recommendation", cascade="all, delete-orphan",
    )
    feedback: Mapped[Optional["FeedbackOutcome"]] = relationship(
        back_populates="recommendation", uselist=False,
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Why this step matters — ties to evidence",
    )
    required_evidence: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True,
        comment="Photo, reading, or check the technician should capture",
    )
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recommendation: Mapped["Recommendation"] = relationship(back_populates="workflow_steps")


class SimilarCase(Base):
    __tablename__ = "similar_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    recommendation_id: Mapped[str] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    service_event_id: Mapped[str] = mapped_column(
        ForeignKey("service_events.id", ondelete="CASCADE"), nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    recommendation: Mapped["Recommendation"] = relationship(back_populates="similar_cases")
    service_event: Mapped["ServiceEvent"] = relationship(
        back_populates="similar_cases", foreign_keys=[service_event_id],
    )


class FeedbackOutcome(Base):
    __tablename__ = "feedback_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    service_event_id: Mapped[str] = mapped_column(
        ForeignKey("service_events.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    recommendation_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True,
    )
    actual_action_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issue_resolved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parts_used: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated parts consumed during the repair",
    )
    feedback_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    technician_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    service_event: Mapped["ServiceEvent"] = relationship(back_populates="feedback")
    recommendation: Mapped[Optional["Recommendation"]] = relationship(back_populates="feedback")


# Resolve forward references
from app.models.master_models import Compressor, IssueCategory  # noqa: E402, F401
from app.models.event_models import ServiceEvent  # noqa: E402, F401
