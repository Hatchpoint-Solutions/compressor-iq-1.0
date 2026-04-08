"""Pydantic schemas for the recommendation engine API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request schemas ───────────────────────────────────────────────────────

class RecommendationGenerateRequest(BaseModel):
    """Input for generating a recommendation."""
    machine_id: Optional[str] = Field(
        None, description="Compressor DB ID (used if no event_id)",
    )
    event_description: Optional[str] = Field(
        None, description="Current event description to augment inference",
    )
    technician_notes: Optional[str] = Field(
        None, description="Current technician notes to augment inference",
    )


class FeedbackCreateRequest(BaseModel):
    """Input for submitting technician feedback."""
    service_event_id: str
    recommendation_id: Optional[str] = None
    actual_action_taken: Optional[str] = None
    issue_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    parts_used: Optional[str] = None
    technician_name: Optional[str] = None
    root_cause: Optional[str] = None


class WorkflowStepUpdateRequest(BaseModel):
    is_completed: Optional[bool] = None
    notes: Optional[str] = None


# ── Lightweight response schemas ──────────────────────────────────────────

class StatusUpdateResponse(BaseModel):
    id: str
    status: str


# ── Response schemas ──────────────────────────────────────────────────────

class WorkflowStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recommendation_id: str
    step_number: int
    instruction: str
    rationale: Optional[str] = None
    required_evidence: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class SimilarCaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_event_id: str
    similarity_score: float
    match_reason: Optional[str] = None


class SimilarCaseDetailResponse(SimilarCaseResponse):
    """Extended similar case with event details for UI display."""
    event_date: Optional[date] = None
    machine_id: Optional[str] = None
    machine_unit_id: Optional[str] = None
    issue_category: Optional[str] = None
    event_category: Optional[str] = None
    action_summary: Optional[str] = None
    resolution_status: Optional[str] = None


class EvidenceSummaryResponse(BaseModel):
    similar_case_count: int = 0
    top_action: Optional[str] = None
    top_action_label: Optional[str] = None
    top_action_frequency: float = 0.0
    resolution_rate: Optional[float] = None
    recent_events_last_30_days: int = 0
    recent_events_last_90_days: int = 0
    recurrence_signal_count: int = 0
    avg_days_between_events: Optional[float] = None


class RecurrenceSignalResponse(BaseModel):
    signal_type: str
    description: str
    event_count: int = 0
    severity: str = "medium"


class RecommendationResponse(BaseModel):
    """Full recommendation response matching the specified output shape."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    service_event_id: Optional[str] = None
    compressor_id: str
    machine_id: Optional[str] = Field(
        None, description="Human-readable unit ID (e.g., MC6068)",
    )

    likely_issue_category: Optional[str] = None
    recommended_action: Optional[str] = None

    confidence_score: float = 0.0
    confidence_label: str = "low"

    explanation: Optional[str] = Field(
        None, alias="reasoning",
        description="Plain-language explanation referencing actual evidence",
    )

    evidence_summary: Optional[dict[str, Any]] = None
    recurrence_signals: Optional[list[dict[str, Any]]] = None
    suggested_parts_or_checks: Optional[list[str]] = None

    similar_case_count: int = 0
    most_frequent_action: Optional[str] = None
    resolution_rate: Optional[float] = None

    fallback_note: Optional[str] = None
    status: str = "pending"
    created_at: Optional[datetime] = None

    recommended_workflow_steps: list[WorkflowStepResponse] = Field(
        default_factory=list, alias="workflow_steps",
    )
    similar_cases: list[SimilarCaseResponse] = Field(default_factory=list)


class HealthAlertItem(BaseModel):
    severity: str = "medium"
    title: str
    description: str
    recommended_action: str


class HealthAssessmentResponse(BaseModel):
    compressor_id: str
    unit_id: str
    overall_health: str = "unknown"
    health_score: float = 0.0
    summary: str = ""
    alerts: list[HealthAlertItem] = Field(default_factory=list)
    recent_event_count_30d: int = 0
    recent_event_count_90d: int = 0
    total_events: int = 0
    current_run_hours: Optional[float] = None
    last_service_date: Optional[date] = None
    top_issues: list[str] = Field(default_factory=list)
    ai_powered: bool = False
    assessed_at: Optional[datetime] = None
    work_orders_created: list[str] = Field(
        default_factory=list,
        description="IDs of system work orders opened from high-severity alerts (deduped)",
    )


class RecommendationListItem(BaseModel):
    """Lightweight recommendation for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    compressor_id: str
    likely_issue_category: Optional[str] = None
    recommended_action: Optional[str] = None
    confidence_score: float = 0.0
    confidence_label: str = "low"
    similar_case_count: int = 0
    status: str = "pending"
    created_at: Optional[datetime] = None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    service_event_id: str
    recommendation_id: Optional[str] = None
    actual_action_taken: Optional[str] = None
    issue_resolved: Optional[bool] = None
    resolution_notes: Optional[str] = None
    parts_used: Optional[str] = None
    feedback_date: Optional[date] = None
    technician_name: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Analytics response schemas ────────────────────────────────────────────

class ActionFrequencyResponse(BaseModel):
    action_type: str
    count: int
    percentage: float


class IssueFrequencyResponse(BaseModel):
    category: str
    count: int
    percentage: float


class RecurrenceSignalDetailResponse(BaseModel):
    signal_type: str
    description: str
    event_count: int
    time_span_days: Optional[int] = None
    severity: str


class AnalyticsSummaryResponse(BaseModel):
    total_events: int = 0
    action_frequencies: list[ActionFrequencyResponse] = Field(default_factory=list)
    issue_frequencies: list[IssueFrequencyResponse] = Field(default_factory=list)
    recurrence_signals: list[RecurrenceSignalDetailResponse] = Field(default_factory=list)
    recent_event_count_30d: int = 0
    recent_event_count_90d: int = 0
    avg_days_between_events: Optional[float] = None
