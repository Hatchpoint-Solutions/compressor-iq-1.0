"""Import management endpoints.

POST /imports/run         — discover + import files
GET  /imports             — list import batches
GET  /imports/{batch_id}  — batch detail with summary
GET  /imports/{batch_id}/issues  — issues for a batch
GET  /imports/{batch_id}/files   — files in a batch
GET  /imports/{batch_id}/raw-rows — raw rows for audit
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.import_models import (
    ImportBatch,
    ImportFile,
    ImportIssueLog,
    ImportSheet,
    RawServiceRow,
)
from app.schemas.import_schemas import (
    ImportBatchResponse,
    ImportBatchSummary,
    ImportFileResponse,
    ImportIssueResponse,
    ImportRunRequest,
    ImportRunResponse,
    ImportSheetResponse,
    RawRowResponse,
)
from app.schemas.common import PaginatedResponse


router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/run", response_model=ImportRunResponse)
def run_import(body: ImportRunRequest, db: Session = Depends(get_db)):
    """Trigger a new import. Scans for files and processes them."""
    from app.services.ingestion.import_service import run_import as _run

    source_dir = body.source_directory
    file_paths = body.file_paths

    if not source_dir and not file_paths:
        source_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )))

    try:
        batch, report = _run(
            db,
            source_directory=source_dir,
            file_paths=file_paths,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ImportRunResponse(
        batch_id=batch.id,
        status=batch.status,
        files_processed=report.files_processed,
        rows_scanned=report.rows_scanned,
        rows_imported=report.rows_imported,
        rows_skipped=report.rows_skipped,
        rows_errored=report.rows_errored,
        compressors_created=report.compressors_created,
        events_created=report.events_created,
        actions_created=report.actions_created,
        issues_by_severity=report.issues_by_severity,
        issues_by_type=report.issues_by_type,
    )


@router.get("/", response_model=list[ImportBatchResponse])
def list_batches(db: Session = Depends(get_db)):
    """List all import batches, newest first."""
    return (
        db.query(ImportBatch)
        .order_by(ImportBatch.started_at.desc())
        .all()
    )


@router.get("/{batch_id}", response_model=ImportBatchSummary)
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    """Batch detail with files and issue counts."""
    batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    files = (
        db.query(ImportFile)
        .filter(ImportFile.batch_id == batch_id)
        .order_by(ImportFile.discovered_at)
        .all()
    )

    issue_counts_raw = (
        db.query(ImportIssueLog.severity, func.count(ImportIssueLog.id))
        .filter(ImportIssueLog.batch_id == batch_id)
        .group_by(ImportIssueLog.severity)
        .all()
    )
    issue_counts = {row[0]: row[1] for row in issue_counts_raw}

    return ImportBatchSummary(
        id=batch.id,
        batch_key=batch.batch_key,
        status=batch.status,
        source_directory=batch.source_directory,
        initiated_by=batch.initiated_by,
        total_files=batch.total_files,
        total_rows_scanned=batch.total_rows_scanned,
        total_rows_imported=batch.total_rows_imported,
        total_rows_skipped=batch.total_rows_skipped,
        total_rows_errored=batch.total_rows_errored,
        total_issues=batch.total_issues,
        summary_json=batch.summary_json,
        started_at=batch.started_at,
        completed_at=batch.completed_at,
        files=files,
        issue_counts=issue_counts,
    )


@router.get("/{batch_id}/issues", response_model=PaginatedResponse[ImportIssueResponse])
def list_issues(
    batch_id: str,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List data quality issues for a batch."""
    q = db.query(ImportIssueLog).filter(ImportIssueLog.batch_id == batch_id)
    if severity:
        q = q.filter(ImportIssueLog.severity == severity)
    if issue_type:
        q = q.filter(ImportIssueLog.issue_type == issue_type)

    total = q.count()
    items = (
        q.order_by(ImportIssueLog.row_number.asc().nullslast(), ImportIssueLog.created_at)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{batch_id}/files", response_model=list[ImportFileResponse])
def list_batch_files(batch_id: str, db: Session = Depends(get_db)):
    return (
        db.query(ImportFile)
        .filter(ImportFile.batch_id == batch_id)
        .order_by(ImportFile.discovered_at)
        .all()
    )


@router.get("/{batch_id}/raw-rows", response_model=PaginatedResponse[RawRowResponse])
def list_raw_rows(
    batch_id: str,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List raw rows for audit / traceability."""
    q = (
        db.query(RawServiceRow)
        .join(ImportSheet)
        .join(ImportFile)
        .filter(ImportFile.batch_id == batch_id)
    )
    if status:
        q = q.filter(RawServiceRow.normalization_status == status)

    total = q.count()
    items = (
        q.order_by(RawServiceRow.row_number)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)
