"""Stage 6: Issue logging.

Persists validation issues and data quality warnings to the
``import_issue_log`` table for audit and review.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.import_models import ImportIssueLog
from app.services.ingestion.validator import ValidationIssue


def log_issue(
    db: Session,
    *,
    batch_id: str,
    file_id: Optional[str] = None,
    sheet_id: Optional[str] = None,
    raw_row_id: Optional[str] = None,
    row_number: Optional[int] = None,
    issue: ValidationIssue,
) -> ImportIssueLog:
    """Create a single issue log record and add it to the session."""
    record = ImportIssueLog(
        batch_id=batch_id,
        file_id=file_id,
        sheet_id=sheet_id,
        raw_row_id=raw_row_id,
        row_number=row_number,
        severity=issue.severity,
        issue_type=issue.issue_type,
        issue_description=issue.issue_description,
        source_column=issue.source_column,
        source_value=str(issue.source_value)[:2000] if issue.source_value else None,
        suggested_fix=issue.suggested_fix,
    )
    db.add(record)
    return record


def log_issues_batch(
    db: Session,
    *,
    batch_id: str,
    file_id: Optional[str] = None,
    sheet_id: Optional[str] = None,
    raw_row_id: Optional[str] = None,
    row_number: Optional[int] = None,
    issues: list[ValidationIssue],
) -> list[ImportIssueLog]:
    """Persist multiple issues at once."""
    return [
        log_issue(
            db,
            batch_id=batch_id,
            file_id=file_id,
            sheet_id=sheet_id,
            raw_row_id=raw_row_id,
            row_number=row_number,
            issue=issue,
        )
        for issue in issues
    ]


def log_custom_issue(
    db: Session,
    *,
    batch_id: str,
    severity: str,
    issue_type: str,
    description: str,
    file_id: Optional[str] = None,
    sheet_id: Optional[str] = None,
    raw_row_id: Optional[str] = None,
    row_number: Optional[int] = None,
    source_column: Optional[str] = None,
    source_value: Optional[str] = None,
    suggested_fix: Optional[str] = None,
) -> ImportIssueLog:
    """Log a custom issue not originating from the validator."""
    record = ImportIssueLog(
        batch_id=batch_id,
        file_id=file_id,
        sheet_id=sheet_id,
        raw_row_id=raw_row_id,
        row_number=row_number,
        severity=severity,
        issue_type=issue_type,
        issue_description=description,
        source_column=source_column,
        source_value=str(source_value)[:2000] if source_value else None,
        suggested_fix=suggested_fix,
    )
    db.add(record)
    return record
