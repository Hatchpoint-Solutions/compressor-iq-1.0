"""Schemas for fleet-level maintenance analytics and entity comparison."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CostPeriodPoint(BaseModel):
    """Maintenance cost aggregated to a calendar month or year."""

    period: str
    total_cost: float = 0.0
    event_count: int = 0


class FleetAgingPoint(BaseModel):
    """Proxy for fleet wear: average recorded run hours at service events in each period."""

    period: str
    avg_run_hours_at_service: Optional[float] = None
    events_with_run_hours: int = 0


class FleetRunHoursSnapshot(BaseModel):
    """Point-in-time fleet utilization from compressor master data."""

    compressor_count: int = 0
    avg_current_run_hours: Optional[float] = None
    median_current_run_hours: Optional[float] = None
    avg_age_years: Optional[float] = None


class FleetMaintenanceOverview(BaseModel):
    """Descriptive fleet analytics for charts and KPIs."""

    granularity: Literal["month", "year"]
    date_from: date
    date_to: date
    cost_series: list[CostPeriodPoint] = Field(default_factory=list)
    total_maintenance_cost: float = 0.0
    corrective_cost: float = 0.0
    preventive_cost: float = 0.0
    other_cost: float = 0.0
    corrective_event_count: int = 0
    preventive_event_count: int = 0
    other_event_count: int = 0
    fleet_aging_series: list[FleetAgingPoint] = Field(default_factory=list)
    fleet_run_hours_snapshot: FleetRunHoursSnapshot = Field(default_factory=FleetRunHoursSnapshot)


class AnalyticsEntityOption(BaseModel):
    """Selectable compressor or site for comparison."""

    id: str
    label: str


class CompareEntityMetrics(BaseModel):
    """Aggregated maintenance metrics for one compressor or site over a window."""

    entity_id: str
    label: str
    total_cost: float = 0.0
    event_count: int = 0
    corrective_cost: float = 0.0
    preventive_cost: float = 0.0
    other_cost: float = 0.0
    avg_order_cost: Optional[float] = None
    avg_run_hours_at_event: Optional[float] = None


class FleetCompareResponse(BaseModel):
    """Side-by-side metrics for multiple entities (minimum two)."""

    entity_type: Literal["compressor", "site"]
    date_from: date
    date_to: date
    entities: list[CompareEntityMetrics] = Field(default_factory=list)
