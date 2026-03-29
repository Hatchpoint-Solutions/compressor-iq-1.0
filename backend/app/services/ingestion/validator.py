"""Stage 5: Business rule validation.

Applies data quality rules to a mapped + normalised row and returns a list
of issues.  Issues with severity 'error' prevent the row from being written
to the core application tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional


@dataclass
class ValidationIssue:
    severity: str          # info | warning | error
    issue_type: str
    issue_description: str
    source_column: Optional[str] = None
    source_value: Optional[str] = None
    suggested_fix: Optional[str] = None


@dataclass
class ValidationResult:
    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)


def validate_row(mapped_data: dict[str, Any], row_number: int) -> ValidationResult:
    """Apply all validation rules to a single mapped row.

    Parameters
    ----------
    mapped_data : dict
        Row data keyed by target field names (after column mapping).
    row_number : int
        1-based row number in the source sheet.

    Returns
    -------
    ValidationResult
        Contains ``is_valid`` flag and a list of issues.
    """
    issues: list[ValidationIssue] = []

    _check_required_order_description(mapped_data, issues)
    _check_machine_id(mapped_data, issues)
    _check_event_date(mapped_data, issues)
    _check_technician_notes(mapped_data, issues)
    _check_order_cost(mapped_data, issues)
    _check_run_hours(mapped_data, issues)
    _check_plant_code(mapped_data, issues)

    has_errors = any(i.severity == "error" for i in issues)
    return ValidationResult(is_valid=not has_errors, issues=issues)


# ── Individual validation rules ───────────────────────────────────────────

def _check_required_order_description(data: dict, issues: list[ValidationIssue]) -> None:
    val = data.get("order_and_description")
    if not val or str(val).strip() == "":
        issues.append(ValidationIssue(
            severity="error",
            issue_type="missing_order_description",
            issue_description="Order & Description field is empty — cannot derive order number or unit ID",
            source_column="Order & Description",
            source_value=str(val) if val else None,
        ))


def _check_machine_id(data: dict, issues: list[ValidationIssue]) -> None:
    """The machine ID is derived from Order & Description after parsing."""
    val = data.get("order_and_description", "")
    if val:
        parts = str(val).split(" - ", maxsplit=2)
        unit_raw = parts[1].strip() if len(parts) > 1 else ""
        if not unit_raw:
            issues.append(ValidationIssue(
                severity="error",
                issue_type="missing_machine_id",
                issue_description="Cannot extract machine ID from Order & Description",
                source_column="Order & Description",
                source_value=str(val),
                suggested_fix="Verify the compound field format: 'ORDER# - UNIT_ID - DESC'",
            ))


def _check_event_date(data: dict, issues: list[ValidationIssue]) -> None:
    reading_date = data.get("reading_date")
    if not reading_date or str(reading_date).strip() in ("", "nan", "None", "NaT"):
        issues.append(ValidationIssue(
            severity="warning",
            issue_type="missing_reading_date",
            issue_description="Reading Date is null — will attempt to estimate from description/notes",
            source_column="Reading Date",
            source_value=str(reading_date) if reading_date else None,
            suggested_fix="Date will be estimated from the order description or technician notes",
        ))


def _check_technician_notes(data: dict, issues: list[ValidationIssue]) -> None:
    val = data.get("technician_notes")
    if not val or str(val).strip() == "":
        issues.append(ValidationIssue(
            severity="info",
            issue_type="empty_technician_notes",
            issue_description="Order Review Comments field is empty — no actions can be extracted",
            source_column="Order Review Comments",
        ))


def _check_order_cost(data: dict, issues: list[ValidationIssue]) -> None:
    val = data.get("order_cost")
    if val is not None and str(val).strip() not in ("", "nan", "None"):
        try:
            cost = float(str(val).replace(",", ""))
            if cost < 0:
                issues.append(ValidationIssue(
                    severity="warning",
                    issue_type="negative_order_cost",
                    issue_description=f"Order cost is negative: {cost}",
                    source_column="Order Cost",
                    source_value=str(val),
                    suggested_fix="Verify if this is a credit/refund or data error",
                ))
            if cost > 50000:
                issues.append(ValidationIssue(
                    severity="info",
                    issue_type="high_order_cost",
                    issue_description=f"Order cost is unusually high: {cost}",
                    source_column="Order Cost",
                    source_value=str(val),
                ))
        except (ValueError, TypeError):
            issues.append(ValidationIssue(
                severity="warning",
                issue_type="invalid_order_cost",
                issue_description=f"Cannot parse order cost as number",
                source_column="Order Cost",
                source_value=str(val),
            ))


def _check_run_hours(data: dict, issues: list[ValidationIssue]) -> None:
    val = data.get("run_hours")
    if val is not None and str(val).strip() not in ("", "nan", "None"):
        try:
            hours = float(str(val).replace(",", ""))
            if hours < 0:
                issues.append(ValidationIssue(
                    severity="error",
                    issue_type="negative_run_hours",
                    issue_description=f"Run hours is negative: {hours}",
                    source_column="Run Hours",
                    source_value=str(val),
                ))
            if hours > 200000:
                issues.append(ValidationIssue(
                    severity="warning",
                    issue_type="extreme_run_hours",
                    issue_description=f"Run hours exceeds 200,000: {hours}",
                    source_column="Run Hours",
                    source_value=str(val),
                ))
        except (ValueError, TypeError):
            issues.append(ValidationIssue(
                severity="warning",
                issue_type="invalid_run_hours",
                issue_description="Cannot parse run hours as number",
                source_column="Run Hours",
                source_value=str(val),
            ))


def _check_plant_code(data: dict, issues: list[ValidationIssue]) -> None:
    val = data.get("plant_code")
    if val and len(str(val).strip()) > 10:
        issues.append(ValidationIssue(
            severity="error",
            issue_type="invalid_plant_code",
            issue_description="Plant code is too long — likely a metadata/footer row",
            source_column="Plant",
            source_value=str(val)[:100],
            suggested_fix="Skip this row — it contains spreadsheet filter metadata",
        ))
