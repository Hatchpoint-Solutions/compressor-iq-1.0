"""Stage 3: Source-to-target column mapping.

Defines the explicit mapping from spreadsheet column names to internal
field names and provides transformation rules.

This mapping is configurable — if a new spreadsheet variant arrives with
slightly different column names, only this file needs updating.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ColumnMapping:
    source_column: str
    target_field: str
    required: bool = False
    transform: Optional[str] = None
    notes: str = ""


# ── Source-to-target mapping for the MC6068-style SAP export ──────────────
#
# The mapping is ordered by target field importance.  The ``transform``
# field documents what will happen to the raw value during normalisation.

COLUMN_MAPPINGS: list[ColumnMapping] = [
    ColumnMapping(
        source_column="Plant",
        target_field="plant_code",
        required=False,
        transform="strip; validate 4-digit numeric",
        notes="Site/location. Row is metadata if not 4 digits.",
    ),
    ColumnMapping(
        source_column="Order & Description",
        target_field="order_and_description",
        required=True,
        transform="split on ' - ' → order_number, unit_id_raw, order_description",
        notes="Compound field: 'ORDER# - UNIT_ID - DESCRIPTION'",
    ),
    ColumnMapping(
        source_column="Customer Name",
        target_field="customer_name",
        required=False,
        transform="strip; title case normalisation",
    ),
    ColumnMapping(
        source_column="Equipment",
        target_field="equipment_number",
        required=False,
        transform="strip; convert float to int string",
        notes="SAP equipment number. All rows = 500021946 in current data.",
    ),
    ColumnMapping(
        source_column="Type",
        target_field="order_type",
        required=False,
        transform="strip; uppercase",
        notes="SAP order type: ZNS1 (service), ZNS6 (PM)",
    ),
    ColumnMapping(
        source_column="Order Review Comments",
        target_field="technician_notes",
        required=False,
        transform="preserve verbatim as raw; strip for cleaned version",
        notes="Rich free-text field. Primary source for action/date extraction.",
    ),
    ColumnMapping(
        source_column="Order Status",
        target_field="order_status",
        required=False,
        transform="strip; uppercase",
        notes="TECO, Closed, Released, Created",
    ),
    ColumnMapping(
        source_column="User Status",
        target_field="user_status",
        required=False,
        transform="strip; uppercase",
        notes="SMOK, CRTD, SPCC",
    ),
    ColumnMapping(
        source_column="Maintenance Activity Type",
        target_field="maintenance_activity_type_raw",
        required=False,
        transform="preserve raw; map code → normalised label",
        notes="ZUR → unscheduled_repair; ZPM → preventive_maintenance; ZPR → preservation",
    ),
    ColumnMapping(
        source_column="Order Cost",
        target_field="order_cost",
        required=False,
        transform="parse float; log if negative or > 100k",
    ),
    ColumnMapping(
        source_column="Order Revenue",
        target_field="order_revenue",
        required=False,
        transform="parse float",
        notes="Always 0 in current data — preserved for completeness.",
    ),
    ColumnMapping(
        source_column="Currency",
        target_field="currency",
        required=False,
        transform="strip; uppercase; default USD",
    ),
    ColumnMapping(
        source_column="Run Hours",
        target_field="run_hours",
        required=False,
        transform="parse float; validate range 0–200000",
    ),
    ColumnMapping(
        source_column="Reading Date",
        target_field="reading_date",
        required=False,
        transform="parse datetime; fallback multiple formats; log failures",
    ),
]

# Fast lookup by source column name
_SOURCE_LOOKUP: dict[str, ColumnMapping] = {m.source_column: m for m in COLUMN_MAPPINGS}

# Case-insensitive + whitespace-normalized lookup for fuzzy matching
_NORMALIZED_LOOKUP: dict[str, ColumnMapping] = {
    m.source_column.strip().lower().replace("  ", " "): m for m in COLUMN_MAPPINGS
}

# Columns that are always empty or carry no useful information
IGNORED_COLUMNS: set[str] = {"GM %", "Days to Inv.", "Category", "Sub-Orders", "Lead Order"}


def _fuzzy_match(col_name: str) -> Optional[ColumnMapping]:
    """Try to match a column name using case-insensitive and whitespace-normalized lookup."""
    normalized = col_name.strip().lower().replace("  ", " ")
    return _NORMALIZED_LOOKUP.get(normalized)


def map_row(raw_row: dict[str, Any], column_names: list[str]) -> dict[str, Any]:
    """Map a raw row dict from source column names to internal target names.

    Returns a new dict keyed by ``target_field`` with raw string values.
    Columns not in the mapping are silently skipped.
    """
    mapped: dict[str, Any] = {}
    for col_name in column_names:
        if col_name in IGNORED_COLUMNS:
            continue
        mapping = _SOURCE_LOOKUP.get(col_name) or _fuzzy_match(col_name)
        if mapping is None:
            continue
        mapped[mapping.target_field] = raw_row.get(col_name)
    return mapped


def validate_column_compatibility(column_names: list[str]) -> tuple[list[str], list[str]]:
    """Check how many source columns can be mapped.

    Returns (matched_columns, unmatched_required_columns).
    """
    matched = []
    for col_name in column_names:
        if col_name in IGNORED_COLUMNS:
            continue
        mapping = _SOURCE_LOOKUP.get(col_name) or _fuzzy_match(col_name)
        if mapping:
            matched.append(col_name)

    required_targets = {m.target_field for m in COLUMN_MAPPINGS if m.required}
    matched_targets = set()
    for col_name in matched:
        mapping = _SOURCE_LOOKUP.get(col_name) or _fuzzy_match(col_name)
        if mapping:
            matched_targets.add(mapping.target_field)

    missing_required = [t for t in required_targets if t not in matched_targets]
    return matched, missing_required


def get_required_fields() -> list[str]:
    """Return target field names that are required."""
    return [m.target_field for m in COLUMN_MAPPINGS if m.required]


def get_mapping_for_source(source_col: str) -> Optional[ColumnMapping]:
    return _SOURCE_LOOKUP.get(source_col) or _fuzzy_match(source_col)
