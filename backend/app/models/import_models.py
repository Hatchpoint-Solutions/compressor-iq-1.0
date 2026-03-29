"""Import / audit zone models.

These tables form the raw-data preservation layer. Every spreadsheet import
is tracked at batch → file → sheet → row granularity so that any normalized
record can be traced back to its original source cell.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class ImportBatch(Base):
    """One logical import run — may cover multiple files."""

    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_key: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, nullable=True,
        comment="Idempotency key (e.g. hash of file set)",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending | processing | completed | failed",
    )
    source_directory: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    initiated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_rows_scanned: Mapped[int] = mapped_column(Integer, default=0)
    total_rows_imported: Mapped[int] = mapped_column(Integer, default=0)
    total_rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    total_rows_errored: Mapped[int] = mapped_column(Integer, default=0)
    total_issues: Mapped[int] = mapped_column(Integer, default=0)

    summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    files: Mapped[list["ImportFile"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan",
    )
    issues: Mapped[list["ImportIssueLog"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan",
    )


class ImportFile(Base):
    """A single file processed within an import batch."""

    __tablename__ = "import_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True, index=True,
        comment="SHA-256 of file contents for dedup",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="xlsx | xls | csv | tsv")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="discovered")
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    batch: Mapped["ImportBatch"] = relationship(back_populates="files")
    sheets: Mapped[list["ImportSheet"]] = relationship(
        back_populates="file", cascade="all, delete-orphan",
    )
    issues: Mapped[list["ImportIssueLog"]] = relationship(back_populates="file")


class ImportSheet(Base):
    """Metadata for one worksheet / CSV within an import file."""

    __tablename__ = "import_sheets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    file_id: Mapped[str] = mapped_column(
        ForeignKey("import_files.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    sheet_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sheet_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    column_count: Mapped[int] = mapped_column(Integer, default=0)
    column_names_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    file: Mapped["ImportFile"] = relationship(back_populates="sheets")
    raw_rows: Mapped[list["RawServiceRow"]] = relationship(
        back_populates="sheet", cascade="all, delete-orphan",
    )
    issues: Mapped[list["ImportIssueLog"]] = relationship(back_populates="sheet")


class RawServiceRow(Base):
    """Verbatim preservation of every source row as imported.

    The ``raw_data_json`` field stores every column value exactly as read from
    the spreadsheet.  ``mapped_data_json`` holds the result after column-name
    mapping.  ``normalization_status`` tracks how far through the pipeline the
    row has progressed.
    """

    __tablename__ = "raw_service_rows"
    __table_args__ = (
        Index("ix_raw_row_hash", "row_hash"),
        Index("ix_raw_row_sheet_row", "sheet_id", "row_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sheet_id: Mapped[str] = mapped_column(
        ForeignKey("import_sheets.id", ondelete="CASCADE"), nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="1-based row in source sheet")
    row_hash: Mapped[str] = mapped_column(
        String(128), nullable=False,
        comment="SHA-256 fingerprint of row content for dedup",
    )

    raw_data_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    mapped_data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    normalization_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="pending | mapped | normalized | validated | imported | skipped | errored",
    )

    normalized_event_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("service_events.id", ondelete="SET NULL"), nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    sheet: Mapped["ImportSheet"] = relationship(back_populates="raw_rows")


class ImportIssueLog(Base):
    """Data quality issue detected during import."""

    __tablename__ = "import_issue_log"
    __table_args__ = (
        Index("ix_issue_batch_severity", "batch_id", "severity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    batch_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False,
    )
    file_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("import_files.id", ondelete="SET NULL"), nullable=True,
    )
    sheet_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("import_sheets.id", ondelete="SET NULL"), nullable=True,
    )
    raw_row_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("raw_service_rows.id", ondelete="SET NULL"), nullable=True,
    )
    row_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    severity: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="info | warning | error",
    )
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    source_column: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_fix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    batch: Mapped["ImportBatch"] = relationship(back_populates="issues")
    file: Mapped[Optional["ImportFile"]] = relationship(back_populates="issues")
    sheet: Mapped[Optional["ImportSheet"]] = relationship(back_populates="issues")
