"""Schemas for import / audit endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ImportRunRequest(BaseModel):
    source_directory: Optional[str] = Field(
        None, description="Directory to scan. If omitted, scans the project root.",
    )
    file_paths: Optional[list[str]] = Field(
        None, description="Explicit file paths to import.",
    )


class ImportRunResponse(BaseModel):
    batch_id: str
    status: str
    files_processed: int = 0
    rows_scanned: int = 0
    rows_imported: int = 0
    rows_skipped: int = 0
    rows_errored: int = 0
    compressors_created: int = 0
    events_created: int = 0
    actions_created: int = 0
    issues_by_severity: dict[str, int] = Field(default_factory=dict)
    issues_by_type: dict[str, int] = Field(default_factory=dict)


class ImportFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    batch_id: str
    file_name: str
    file_path: str
    file_hash: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_type: str
    status: str
    row_count: Optional[int] = None
    sheet_count: Optional[int] = None
    discovered_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class ImportSheetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    file_id: str
    sheet_name: str
    sheet_index: int
    row_count: int = 0
    column_count: int = 0
    column_names_json: Optional[list] = None
    status: str


class RawRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    sheet_id: str
    row_number: int
    row_hash: str
    raw_data_json: dict
    mapped_data_json: Optional[dict] = None
    normalization_status: str
    normalized_event_id: Optional[str] = None
    created_at: Optional[datetime] = None


class ImportIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    batch_id: str
    file_id: Optional[str] = None
    sheet_id: Optional[str] = None
    raw_row_id: Optional[str] = None
    row_number: Optional[int] = None
    severity: str
    issue_type: str
    issue_description: str
    source_column: Optional[str] = None
    source_value: Optional[str] = None
    suggested_fix: Optional[str] = None
    created_at: Optional[datetime] = None


class ImportBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    batch_key: Optional[str] = None
    status: str
    source_directory: Optional[str] = None
    initiated_by: Optional[str] = None
    total_files: int = 0
    total_rows_scanned: int = 0
    total_rows_imported: int = 0
    total_rows_skipped: int = 0
    total_rows_errored: int = 0
    total_issues: int = 0
    summary_json: Optional[dict] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ImportBatchSummary(ImportBatchResponse):
    files: list[ImportFileResponse] = Field(default_factory=list)
    issue_counts: dict[str, int] = Field(default_factory=dict)
