"""Schemas for dashboard endpoints."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class TopIssueItem(BaseModel):
    category: str
    count: int
    percentage: float = 0.0


class MachineAttentionItem(BaseModel):
    compressor_id: str
    unit_id: str
    recent_event_count: int
    last_event_category: Optional[str] = None
    last_event_date: Optional[date] = None


class DashboardSummary(BaseModel):
    total_events: int = 0
    total_compressors: int = 0
    recent_events_count: int = 0
    corrective_count: int = 0
    preventive_count: int = 0
    avg_cost: Optional[float] = None
    top_issues: list[TopIssueItem] = Field(default_factory=list)
    machines_needing_attention: list[MachineAttentionItem] = Field(default_factory=list)


class EventStats(BaseModel):
    by_category: dict[str, int] = Field(default_factory=dict)
    by_month: dict[str, int] = Field(default_factory=dict)
    by_activity_type: dict[str, int] = Field(default_factory=dict)
    total_cost: Optional[float] = None
    avg_cost: Optional[float] = None
