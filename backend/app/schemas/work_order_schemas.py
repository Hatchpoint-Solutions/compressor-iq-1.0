"""Pydantic schemas for work orders."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkOrderStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    work_order_id: str
    step_number: int
    instruction: str
    rationale: Optional[str] = None
    required_evidence: Optional[str] = None
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class WorkOrderListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str] = None
    compressor_id: str
    unit_id: str = Field(
        "",
        description="Resolved at read time from compressor",
    )
    source: str
    status: str
    assigned_technician_id: Optional[str] = None
    assigned_technician_name: Optional[str] = None
    recommendation_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkOrderDetail(WorkOrderListItem):
    steps: list[WorkOrderStepResponse] = Field(default_factory=list)


class WorkOrderCreate(BaseModel):
    compressor_id: str = Field(..., description="Compressor UUID")
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    source: str = Field("ad_hoc", description="predictive | ad_hoc | system")
    recommendation_id: Optional[str] = Field(
        None,
        description="If set, steps are copied from this recommendation's workflow",
    )
    issue_category: Optional[str] = Field(
        None,
        description="Required for ad_hoc when recommendation_id is omitted — drives generated workflow",
    )
    assigned_technician_id: Optional[str] = None


class WorkOrderUpdate(BaseModel):
    status: Optional[str] = Field(
        None,
        description="open | in_progress | completed | cancelled",
    )
    assigned_technician_id: Optional[str] = None
    clear_assigned_technician: bool = False
    title: Optional[str] = Field(None, max_length=300)
    description: Optional[str] = None


class WorkOrderStepUpdate(BaseModel):
    is_completed: Optional[bool] = None
    notes: Optional[str] = None


class TechnicianListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    event_count: int = 0
