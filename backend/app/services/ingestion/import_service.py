"""Stage 8: Import orchestrator.

Coordinates the full 10-stage ingestion pipeline:

  1. Discover files
  2. Register import batch + file metadata
  3. Read workbook sheets
  4. Persist raw rows
  5. Map source columns
  6. Normalise values
  7. Validate business rules
  8. Write normalised records to core tables
  9. Log issues and summary stats
 10. Produce import report

The pipeline is designed to be re-runnable: duplicate files (by SHA-256) and
duplicate rows (by content fingerprint) are detected and skipped.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.import_models import (
    ImportBatch,
    ImportFile,
    ImportIssueLog,
    ImportSheet,
    RawServiceRow,
)
from app.models.master_models import (
    Compressor,
    IssueCategory,
    MaintenanceActionType,
    Site,
    Technician,
)
from app.models.event_models import (
    ServiceEvent,
    ServiceEventAction,
    ServiceEventMeasurement,
    ServiceEventNote,
)
from app.services.ingestion.file_discovery import DiscoveredFile, discover_files
from app.services.ingestion.workbook_reader import SheetData, read_workbook
from app.services.ingestion.source_mapper import IGNORED_COLUMNS, map_row
from app.services.ingestion.normalizer import (
    classify_event_category,
    clean_technician_notes,
    estimate_event_date,
    extract_actions_from_notes,
    extract_notes_entries,
    infer_issue_category,
    normalize_activity_type,
    normalize_date,
    normalize_equipment_number,
    normalize_float,
    normalize_plant_code,
    normalize_unit_id,
    parse_order_and_description,
)
from app.services.ingestion.validator import ValidationIssue, validate_row
from app.services.ingestion.issue_logger import log_custom_issue, log_issues_batch
from app.services.ingestion.deduplication import (
    is_duplicate_order_number,
    is_duplicate_raw_row,
)
from app.utils.hashing import file_sha256, row_fingerprint

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Import report dataclass
# ═══════════════════════════════════════════════════════════════════════════

class ImportReport:
    """Collects counters throughout the pipeline and produces a summary."""

    def __init__(self) -> None:
        self.files_processed: int = 0
        self.sheets_processed: int = 0
        self.rows_scanned: int = 0
        self.rows_imported: int = 0
        self.rows_skipped: int = 0
        self.rows_errored: int = 0
        self.rows_duplicate: int = 0
        self.compressors_created: int = 0
        self.sites_created: int = 0
        self.technicians_created: int = 0
        self.events_created: int = 0
        self.actions_created: int = 0
        self.notes_created: int = 0
        self.measurements_created: int = 0
        self.issues_by_severity: dict[str, int] = {"info": 0, "warning": 0, "error": 0}
        self.issues_by_type: dict[str, int] = {}

    def record_issue(self, severity: str, issue_type: str) -> None:
        self.issues_by_severity[severity] = self.issues_by_severity.get(severity, 0) + 1
        self.issues_by_type[issue_type] = self.issues_by_type.get(issue_type, 0) + 1

    def to_dict(self) -> dict:
        return {
            "files_processed": self.files_processed,
            "sheets_processed": self.sheets_processed,
            "rows_scanned": self.rows_scanned,
            "rows_imported": self.rows_imported,
            "rows_skipped": self.rows_skipped,
            "rows_errored": self.rows_errored,
            "rows_duplicate": self.rows_duplicate,
            "compressors_created": self.compressors_created,
            "sites_created": self.sites_created,
            "technicians_created": self.technicians_created,
            "events_created": self.events_created,
            "actions_created": self.actions_created,
            "notes_created": self.notes_created,
            "measurements_created": self.measurements_created,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_type": self.issues_by_type,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Main pipeline entry point
# ═══════════════════════════════════════════════════════════════════════════

def run_import(
    db: Session,
    source_directory: str | None = None,
    file_paths: list[str] | None = None,
    initiated_by: str | None = None,
) -> tuple[ImportBatch, ImportReport]:
    """Execute the full import pipeline.

    Parameters
    ----------
    db : Session
        Active database session.
    source_directory : str, optional
        Directory to scan for files.  Mutually exclusive with *file_paths*.
    file_paths : list[str], optional
        Explicit list of file paths to import.
    initiated_by : str, optional
        Username or system identifier that triggered the import.

    Returns
    -------
    (ImportBatch, ImportReport)
    """
    report = ImportReport()

    # ── Stage 1: Discover files ───────────────────────────────────────────
    if file_paths:
        discovered = [
            DiscoveredFile(
                file_name=Path(p).name,
                file_path=str(Path(p).resolve()),
                file_type=Path(p).suffix.lstrip(".").lower(),
                file_size_bytes=Path(p).stat().st_size if Path(p).exists() else 0,
            )
            for p in file_paths
        ]
    elif source_directory:
        discovered = discover_files(source_directory)
    else:
        raise ValueError("Either source_directory or file_paths must be provided")

    if not discovered:
        raise ValueError(f"No importable files found in {source_directory or file_paths}")

    # ── Stage 2: Register batch ───────────────────────────────────────────
    batch = ImportBatch(
        status="processing",
        source_directory=source_directory,
        initiated_by=initiated_by,
        total_files=len(discovered),
    )
    db.add(batch)
    db.flush()

    try:
        for disc_file in discovered:
            _process_single_file(db, batch, disc_file, report)
            report.files_processed += 1

        # ── Stage 10: Finalise ────────────────────────────────────────────
        batch.status = "completed"
        batch.completed_at = datetime.now(timezone.utc)
        batch.total_rows_scanned = report.rows_scanned
        batch.total_rows_imported = report.rows_imported
        batch.total_rows_skipped = report.rows_skipped
        batch.total_rows_errored = report.rows_errored
        batch.total_issues = sum(report.issues_by_severity.values())
        batch.summary_json = report.to_dict()
        db.commit()

    except Exception:
        db.rollback()
        batch.status = "failed"
        batch.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise

    return batch, report


# ═══════════════════════════════════════════════════════════════════════════
# File-level processing
# ═══════════════════════════════════════════════════════════════════════════

def _process_single_file(
    db: Session,
    batch: ImportBatch,
    disc_file: DiscoveredFile,
    report: ImportReport,
) -> None:
    """Process one file through stages 2-9."""

    file_hash = file_sha256(disc_file.file_path)

    existing_file = (
        db.query(ImportFile)
        .filter(ImportFile.file_hash == file_hash)
        .first()
    )
    if existing_file:
        log_custom_issue(
            db,
            batch_id=batch.id,
            severity="info",
            issue_type="duplicate_file",
            description=f"File already imported (hash match): {disc_file.file_name}",
            source_value=file_hash,
        )
        report.record_issue("info", "duplicate_file")
        return

    import_file = ImportFile(
        batch_id=batch.id,
        file_name=disc_file.file_name,
        file_path=disc_file.file_path,
        file_hash=file_hash,
        file_size_bytes=disc_file.file_size_bytes,
        file_type=disc_file.file_type,
        status="processing",
    )
    db.add(import_file)
    db.flush()

    # ── Stage 3: Read workbook ────────────────────────────────────────────
    workbook = read_workbook(disc_file.file_path, disc_file.file_type)
    import_file.sheet_count = len(workbook.sheets)

    total_rows = 0
    for sheet_data in workbook.sheets:
        _process_single_sheet(db, batch, import_file, sheet_data, report)
        total_rows += sheet_data.row_count
        report.sheets_processed += 1

    import_file.row_count = total_rows
    import_file.status = "completed"
    import_file.processed_at = datetime.now(timezone.utc)
    db.flush()


# ═══════════════════════════════════════════════════════════════════════════
# Sheet-level processing
# ═══════════════════════════════════════════════════════════════════════════

def _process_single_sheet(
    db: Session,
    batch: ImportBatch,
    import_file: ImportFile,
    sheet_data: SheetData,
    report: ImportReport,
) -> None:
    """Process one sheet through stages 4-9."""

    import_sheet = ImportSheet(
        file_id=import_file.id,
        sheet_name=sheet_data.sheet_name,
        sheet_index=sheet_data.sheet_index,
        row_count=sheet_data.row_count,
        column_count=sheet_data.column_count,
        column_names_json=sheet_data.column_names,
        status="processing",
    )
    db.add(import_sheet)
    db.flush()

    for row_idx, raw_row in enumerate(sheet_data.rows, start=1):
        report.rows_scanned += 1

        # ── Stage 4: Persist raw row ─────────────────────────────────────
        rh = row_fingerprint(raw_row)

        if is_duplicate_raw_row(db, rh):
            report.rows_duplicate += 1
            report.rows_skipped += 1
            log_custom_issue(
                db, batch_id=batch.id, file_id=import_file.id,
                sheet_id=import_sheet.id, row_number=row_idx,
                severity="info", issue_type="duplicate_row",
                description="Row content fingerprint already exists — skipped",
            )
            report.record_issue("info", "duplicate_row")
            continue

        raw_row_record = RawServiceRow(
            sheet_id=import_sheet.id,
            row_number=row_idx,
            row_hash=rh,
            raw_data_json=raw_row,
            normalization_status="pending",
        )
        db.add(raw_row_record)
        db.flush()

        # ── Stage 5: Map columns ─────────────────────────────────────────
        mapped = map_row(raw_row, sheet_data.column_names)
        raw_row_record.mapped_data_json = mapped
        raw_row_record.normalization_status = "mapped"

        # ── Stage 7: Validate ─────────────────────────────────────────────
        validation = validate_row(mapped, row_idx)
        if validation.issues:
            log_issues_batch(
                db, batch_id=batch.id, file_id=import_file.id,
                sheet_id=import_sheet.id, raw_row_id=raw_row_record.id,
                row_number=row_idx, issues=validation.issues,
            )
            for vi in validation.issues:
                report.record_issue(vi.severity, vi.issue_type)

        if validation.has_errors:
            raw_row_record.normalization_status = "errored"
            report.rows_errored += 1
            continue

        # ── Stage 6 + 8: Normalise and write ─────────────────────────────
        try:
            _normalise_and_persist(
                db, batch, import_file, import_sheet, raw_row_record,
                mapped, row_idx, report,
            )
            raw_row_record.normalization_status = "imported"
            report.rows_imported += 1
        except _SkipRow:
            pass
        except Exception as exc:
            raw_row_record.normalization_status = "errored"
            report.rows_errored += 1
            log_custom_issue(
                db, batch_id=batch.id, file_id=import_file.id,
                sheet_id=import_sheet.id, raw_row_id=raw_row_record.id,
                row_number=row_idx, severity="error",
                issue_type="normalisation_exception",
                description=str(exc)[:2000],
            )
            report.record_issue("error", "normalisation_exception")
            logger.exception("Row %d normalisation failed", row_idx)

    import_sheet.status = "completed"
    db.flush()


# ═══════════════════════════════════════════════════════════════════════════
# Row-level normalisation and persistence
# ═══════════════════════════════════════════════════════════════════════════

def _normalise_and_persist(
    db: Session,
    batch: ImportBatch,
    import_file: ImportFile,
    import_sheet: ImportSheet,
    raw_row_record: RawServiceRow,
    mapped: dict[str, Any],
    row_number: int,
    report: ImportReport,
) -> None:
    """Normalise a single mapped row and write it to the core tables."""

    # ── Parse compound order & description ────────────────────────────────
    raw_order_desc = mapped.get("order_and_description", "")
    order_num, unit_raw, description = parse_order_and_description(raw_order_desc)

    if not order_num:
        raise ValueError("Empty order number after parsing")

    # Skip already-imported orders (idempotency)
    if is_duplicate_order_number(db, order_num):
        raw_row_record.normalization_status = "skipped"
        report.rows_skipped += 1
        report.rows_imported -= 0  # not yet incremented
        log_custom_issue(
            db, batch_id=batch.id, file_id=import_file.id,
            sheet_id=import_sheet.id, raw_row_id=raw_row_record.id,
            row_number=row_number, severity="info",
            issue_type="duplicate_order_number",
            description=f"Order {order_num} already exists — skipped",
        )
        report.record_issue("info", "duplicate_order_number")
        # Adjust so caller doesn't count this as "imported"
        raise _SkipRow()

    # ── Normalise unit ID ─────────────────────────────────────────────────
    unit_result = normalize_unit_id(unit_raw)
    unit_id = unit_result.normalized

    # ── Get or create Compressor ──────────────────────────────────────────
    compressor = db.query(Compressor).filter(Compressor.unit_id == unit_id).first()
    if not compressor:
        equip_result = normalize_equipment_number(mapped.get("equipment_number"))
        compressor = Compressor(
            unit_id=unit_id,
            raw_source_unit_ids=[unit_raw] if unit_raw else [],
            equipment_number=equip_result.normalized,
        )
        db.add(compressor)
        db.flush()
        report.compressors_created += 1
    else:
        existing_raw = compressor.raw_source_unit_ids or []
        if unit_raw and unit_raw not in existing_raw:
            compressor.raw_source_unit_ids = existing_raw + [unit_raw]

    # ── Get or create Site ────────────────────────────────────────────────
    plant_result = normalize_plant_code(mapped.get("plant_code"))
    plant_code = plant_result.normalized
    customer_name = (mapped.get("customer_name") or "").strip() or "Unknown"

    if plant_code:
        site = (
            db.query(Site)
            .filter(Site.plant_code == plant_code, Site.customer_name == customer_name)
            .first()
        )
        if not site:
            site = Site(
                plant_code=plant_code,
                customer_name=customer_name,
                raw_source_names=[customer_name],
            )
            db.add(site)
            db.flush()
            report.sites_created += 1
        else:
            existing_names = site.raw_source_names or []
            if customer_name not in existing_names:
                site.raw_source_names = existing_names + [customer_name]

        if not compressor.site_id:
            compressor.site_id = site.id

    # ── Normalise dates ───────────────────────────────────────────────────
    date_result = normalize_date(mapped.get("reading_date"))
    event_date = date_result.normalized
    event_date_source = "reading_date" if event_date else None
    event_date_estimated = False

    if not event_date:
        est_result = estimate_event_date(raw_order_desc, mapped.get("technician_notes"))
        if est_result.normalized:
            event_date = est_result.normalized
            event_date_source = "estimated_from_text"
            event_date_estimated = True

    # ── Normalise activity type ───────────────────────────────────────────
    activity_result = normalize_activity_type(mapped.get("maintenance_activity_type_raw"))

    # ── Classify event category ───────────────────────────────────────────
    event_category = classify_event_category(description)

    # ── Normalise numeric fields ──────────────────────────────────────────
    run_hours_result = normalize_float(mapped.get("run_hours"), "run_hours")
    cost_result = normalize_float(mapped.get("order_cost"), "order_cost")
    revenue_result = normalize_float(mapped.get("order_revenue"), "order_revenue")

    # ── Clean technician notes ────────────────────────────────────────────
    notes_result = clean_technician_notes(mapped.get("technician_notes"))

    # ── Infer issue category ──────────────────────────────────────────────
    issue_cat_id = None
    if event_category == "corrective" and mapped.get("technician_notes"):
        inferred = infer_issue_category(
            mapped.get("technician_notes"), description,
        )
        if inferred:
            cat_name, severity = inferred
            issue_cat = (
                db.query(IssueCategory).filter(IssueCategory.name == cat_name).first()
            )
            if not issue_cat:
                issue_cat = IssueCategory(
                    name=cat_name,
                    severity_default=severity,
                    detection_keywords=[kw for _, kws, _ in
                                        normalizer_mod().ISSUE_CATEGORY_RULES
                                        if _ == cat_name
                                        for kw in kws] if False else None,
                )
                db.add(issue_cat)
                db.flush()
            issue_cat_id = issue_cat.id

    # ── Create ServiceEvent ───────────────────────────────────────────────
    currency_raw = mapped.get("currency")
    currency = currency_raw.strip().upper() if currency_raw else "USD"

    event = ServiceEvent(
        compressor_id=compressor.id,
        order_number=order_num,
        order_description=description,
        raw_order_and_description=raw_order_desc,
        event_date=event_date,
        event_date_source=event_date_source,
        event_date_estimated=event_date_estimated,
        event_category=event_category,
        maintenance_activity_type_raw=mapped.get("maintenance_activity_type_raw"),
        maintenance_activity_type=activity_result.normalized,
        order_type=mapped.get("order_type"),
        order_status=mapped.get("order_status"),
        user_status=mapped.get("user_status"),
        technician_notes_raw=mapped.get("technician_notes"),
        technician_notes_clean=notes_result.normalized,
        run_hours_at_event=run_hours_result.normalized,
        order_cost=cost_result.normalized,
        order_revenue=revenue_result.normalized,
        currency=currency,
        plant_code=plant_code,
        customer_name=customer_name,
        issue_category_id=issue_cat_id,
        import_batch_id=batch.id,
        import_file_id=import_file.id,
        raw_row_id=raw_row_record.id,
    )
    db.add(event)
    db.flush()
    report.events_created += 1

    raw_row_record.normalized_event_id = event.id

    # ── Create measurements ───────────────────────────────────────────────
    if run_hours_result.normalized is not None:
        db.add(ServiceEventMeasurement(
            service_event_id=event.id,
            measurement_type="run_hours",
            value=run_hours_result.normalized,
            unit="hrs",
            measured_at=event_date,
            source=event_date_source,
        ))
        report.measurements_created += 1
        if (not compressor.current_run_hours
                or run_hours_result.normalized > compressor.current_run_hours):
            compressor.current_run_hours = run_hours_result.normalized

    if cost_result.normalized is not None:
        db.add(ServiceEventMeasurement(
            service_event_id=event.id,
            measurement_type="cost",
            value=cost_result.normalized,
            unit=currency,
            measured_at=event_date,
            source="order_cost",
        ))
        report.measurements_created += 1

    # ── Parse and persist actions ─────────────────────────────────────────
    raw_notes = mapped.get("technician_notes")
    if raw_notes:
        parsed_actions = extract_actions_from_notes(raw_notes)
        for seq, act in enumerate(parsed_actions, start=1):
            tech_id = None
            tech_name_raw = act.get("technician_name_raw")
            if tech_name_raw:
                tech_id = _get_or_create_technician(
                    db, tech_name_raw, act.get("technician_username"), report,
                )

            action_record = ServiceEventAction(
                service_event_id=event.id,
                action_type_raw=act.get("action_type_raw"),
                component=act.get("component"),
                description=act.get("description"),
                technician_id=tech_id,
                technician_name_raw=tech_name_raw,
                action_date=act.get("action_date"),
                run_hours_at_action=act.get("run_hours_at_action"),
                sequence_number=seq,
            )
            db.add(action_record)
            report.actions_created += 1

        # Parse structured note entries
        note_entries = extract_notes_entries(raw_notes)
        for seq, note in enumerate(note_entries, start=1):
            db.add(ServiceEventNote(
                service_event_id=event.id,
                note_type=note["note_type"],
                raw_text=note["raw_text"],
                cleaned_text=None,
                author_name=note.get("author_name"),
                author_username=note.get("author_username"),
                note_date=note.get("note_date"),
                sequence_number=seq,
            ))
            report.notes_created += 1

    # Update compressor first-seen date
    if event_date and (not compressor.first_seen_date or event_date < compressor.first_seen_date):
        compressor.first_seen_date = event_date

    db.flush()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _get_or_create_technician(
    db: Session,
    name_raw: str,
    username: str | None,
    report: ImportReport,
) -> str | None:
    """Resolve or create a Technician record. Returns the technician id."""
    if not name_raw:
        return None

    canonical = name_raw.strip().title()
    tech = db.query(Technician).filter(Technician.name == canonical).first()

    if not tech and username:
        tech = db.query(Technician).filter(Technician.username == username.upper()).first()

    if tech:
        existing = tech.raw_source_names or []
        if name_raw not in existing:
            tech.raw_source_names = existing + [name_raw]
        tech.event_count = (tech.event_count or 0) + 1
        return tech.id

    tech = Technician(
        name=canonical,
        raw_source_names=[name_raw],
        username=username.upper() if username else None,
        event_count=1,
    )
    db.add(tech)
    db.flush()
    report.technicians_created += 1
    return tech.id


class _SkipRow(Exception):
    """Raised to signal that a row should be skipped (not an error)."""
    pass


def normalizer_mod():
    """Lazy import to avoid circular dependency."""
    from app.services.ingestion import normalizer
    return normalizer
