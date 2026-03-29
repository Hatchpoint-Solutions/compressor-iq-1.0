"""Schemas for compressor/asset and master data endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    plant_code: str
    customer_name: str
    name: Optional[str] = None
    region: Optional[str] = None


class CompressorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    unit_id: str
    raw_source_unit_ids: Optional[list[str]] = None
    equipment_number: Optional[str] = None
    compressor_type: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: str = "active"
    current_run_hours: Optional[float] = None
    first_seen_date: Optional[date] = None
    site_id: Optional[str] = None
    created_at: Optional[datetime] = None


class CompressorDetail(CompressorResponse):
    site: Optional[SiteResponse] = None
    total_events: int = 0
    corrective_events: int = 0
    preventive_events: int = 0
    last_service_date: Optional[date] = None


class CompressorIssueFrequency(BaseModel):
    category: str
    count: int
    last_occurrence: Optional[date] = None
    avg_run_hours: Optional[float] = None


class TechnicianResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    raw_source_names: Optional[list[str]] = None
    username: Optional[str] = None
    first_seen_date: Optional[date] = None
    event_count: int = 0
