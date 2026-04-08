"""Notification API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    title: str
    body: Optional[str] = None
    compressor_id: Optional[str] = None
    work_order_id: Optional[str] = None
    technician_id: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class MarkReadResponse(BaseModel):
    id: str
    read_at: Optional[datetime] = None


class MarkAllReadResponse(BaseModel):
    marked_count: int
