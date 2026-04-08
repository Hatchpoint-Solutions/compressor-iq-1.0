"""Schemas for technician / manager directory (configuration)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class NameCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class ManagerListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
