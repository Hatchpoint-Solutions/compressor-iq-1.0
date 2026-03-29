"""Schemas for service event endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ServiceEventActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    service_event_id: str
    action_type_id: Optional[str] = None
    action_type_raw: Optional[str] = None
    component: Optional[str] = None
    description: Optional[str] = None
    technician_id: Optional[str] = None
    technician_name_raw: Optional[str] = None
    action_date: Optional[date] = None
    run_hours_at_action: Optional[float] = None
    sequence_number: int = 1


class ServiceEventNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    service_event_id: str
    note_type: str
    raw_text: str
    cleaned_text: Optional[str] = None
    author_name: Optional[str] = None
    author_username: Optional[str] = None
    note_date: Optional[datetime] = None
    sequence_number: int = 1


class ServiceEventMeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    service_event_id: str
    measurement_type: str
    value: float
    unit: Optional[str] = None
    measured_at: Optional[date] = None
    source: Optional[str] = None


class ServiceEventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    compressor_id: str
    order_number: str
    order_description: Optional[str] = None
    event_date: Optional[date] = None
    event_date_estimated: bool = False
    event_category: Optional[str] = None
    maintenance_activity_type: Optional[str] = None
    order_status: Optional[str] = None
    run_hours_at_event: Optional[float] = None
    order_cost: Optional[float] = None
    plant_code: Optional[str] = None
    customer_name: Optional[str] = None


class ServiceEventDetail(ServiceEventListItem):
    raw_order_and_description: Optional[str] = None
    event_date_source: Optional[str] = None
    maintenance_activity_type_raw: Optional[str] = None
    order_type: Optional[str] = None
    user_status: Optional[str] = None
    technician_notes_raw: Optional[str] = None
    technician_notes_clean: Optional[str] = None
    order_revenue: Optional[float] = None
    currency: str = "USD"
    issue_category_id: Optional[str] = None
    import_batch_id: Optional[str] = None
    import_file_id: Optional[str] = None
    raw_row_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    actions: list[ServiceEventActionResponse] = Field(default_factory=list)
    notes: list[ServiceEventNoteResponse] = Field(default_factory=list)
    measurements: list[ServiceEventMeasurementResponse] = Field(default_factory=list)
    compressor: Optional["CompressorResponse"] = None
    issue_category: Optional["IssueCategoryResponse"] = None


class IssueCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: Optional[str] = None
    severity_default: str = "medium"


# Avoid circular import
from app.schemas.compressor_schemas import CompressorResponse  # noqa: E402

ServiceEventDetail.model_rebuild()
