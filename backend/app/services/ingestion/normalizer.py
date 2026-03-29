"""Stage 4: Value normalisation.

Transforms mapped field values into clean, consistent representations while
preserving original raw text.  Each normaliser returns a ``NormResult`` so
that callers can inspect what changed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional


@dataclass
class NormResult:
    """Result of normalising a single value."""
    raw: Any
    normalized: Any
    was_changed: bool = False
    issues: list[str] = field(default_factory=list)


# ── Maintenance activity type mapping ─────────────────────────────────────

ACTIVITY_TYPE_MAP: dict[str, str] = {
    "ZUR - Unscheduled Repair -Mechanical": "unscheduled_repair",
    "ZPM - Preventative Maintenance": "preventive_maintenance",
    "ZPR - Equipment Preservation": "preservation",
}


# ── Event category classification rules ───────────────────────────────────

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("corrective", ["corrective", "callout", "callouts", "non-pm", "npm"]),
    ("preventive_maintenance", ["pm-1", "pm-2", "routine", "annual", "semi"]),
    ("emissions_inspection", ["emission"]),
    ("oil_sampling", ["oil sample", "engine oil"]),
    ("coolant_sampling", ["coolant sample"]),
    ("packing_maintenance", ["packing"]),
    ("valve_inspection", ["psv", "prv"]),
    ("preservation", ["preservation"]),
    ("unit_wash", ["wash"]),
    ("startup", ["start up", "start-up", "new set"]),
    ("telemetry", ["telemetry", "reliability"]),
]


# ── Issue category inference rules ────────────────────────────────────────

ISSUE_CATEGORY_RULES: list[tuple[str, list[str], str]] = [
    ("detonation", ["detonation", "detination", "detnation"], "high"),
    ("leak", ["leak"], "medium"),
    ("pressure_abnormality", ["pressure", "suction", "discharge"], "medium"),
    ("fuel_system", ["fuel", "btu"], "medium"),
    ("valve_failure", ["valve"], "medium"),
    ("cooling_system", ["coolant", "temperature", "water"], "medium"),
    ("electrical", ["wiring", "sensor", "scanner", "panel"], "medium"),
    ("lubrication", ["oil"], "medium"),
    ("filter_maintenance", ["filter"], "low"),
    ("shutdown", ["shutdown", "shut down", "down on"], "high"),
    ("vibration_noise", ["vibration", "noise"], "medium"),
    ("seal_gasket", ["seal", "gasket", "packing"], "medium"),
]


# ── Action keyword → normalised action type ───────────────────────────────

ACTION_KEYWORDS: dict[str, str] = {
    "replaced": "replaced",
    "installed": "replaced",
    "changed": "replaced",
    "adjusted": "adjusted",
    "adjustment": "adjusted",
    "tuned": "adjusted",
    "calibrat": "calibrated",
    "inspected": "inspected",
    "checked": "inspected",
    "observed": "inspected",
    "cleaned": "cleaned",
    "blew out": "cleaned",
    "emptied": "cleaned",
    "tightened": "tightened",
    "repaired": "repaired",
    "fixed": "repaired",
    "started": "started",
    "loaded": "loaded",
}

COMPONENT_KEYWORDS: dict[str, str] = {
    "spark plug": "spark_plug",
    "plug": "spark_plug",
    "air filter": "air_filter",
    "filter": "filter",
    "oil": "oil",
    "coolant": "coolant",
    "valve": "valve",
    "belt": "belt",
    "hose": "hose",
    "gasket": "gasket",
    "seal": "seal",
    "sensor": "sensor",
    "scanner": "sensor",
    "wiring": "wiring",
    "piston": "piston",
    "cylinder": "cylinder",
    "bearing": "bearing",
    "packing": "packing",
    "fuel": "fuel_system",
    "btu": "fuel_system",
    "bellows": "bellows",
    "compressor": "compressor",
    "engine": "engine",
    "temp": "temperature_system",
    "pressure": "pressure_system",
    "suction": "suction_system",
    "discharge": "discharge_system",
}


# ═══════════════════════════════════════════════════════════════════════════
# Public normalisation functions
# ═══════════════════════════════════════════════════════════════════════════


def normalize_unit_id(raw: str | None) -> NormResult:
    """Normalise a compressor unit identifier.

    Examples:
        " MC6068 "         → MC6068
        "MC6068-CORRECTIVE" → MC6068
        "EF6068"           → MC6068  (EF prefix → MC)
        "COMP101"          → COMP101
    """
    if not raw or str(raw).strip() == "":
        return NormResult(raw=raw, normalized="UNKNOWN", was_changed=True,
                          issues=["Empty unit ID"])

    cleaned = str(raw).strip().upper().replace(" ", "")
    match = re.match(r"((?:MC|EF)\d+)", cleaned)
    if match:
        canonical = match.group(1)
        if canonical.startswith("EF"):
            canonical = "MC" + canonical[2:]
        changed = canonical != str(raw).strip()
        return NormResult(raw=raw, normalized=canonical, was_changed=changed)

    return NormResult(raw=raw, normalized=cleaned, was_changed=cleaned != str(raw).strip(),
                      issues=["Unit ID does not match expected MC/EF pattern"])


def parse_order_and_description(raw: str | None) -> tuple[str, str, str]:
    """Split compound field '4113904 - MC6068 - JANUARY 2020 CALLOUTS'.

    Returns (order_number, unit_id_raw, description).
    """
    if not raw or str(raw).strip() == "":
        return ("", "", "")
    parts = str(raw).split(" - ", maxsplit=2)
    order_num = parts[0].strip() if len(parts) > 0 else ""
    unit_raw = parts[1].strip() if len(parts) > 1 else ""
    description = parts[2].strip() if len(parts) > 2 else ""
    return order_num, unit_raw, description


def normalize_date(raw: Any) -> NormResult:
    """Parse a date from various formats.

    Supports: datetime objects, ISO strings, US-format strings.
    """
    if raw is None or str(raw).strip() in ("", "nan", "NaT", "None"):
        return NormResult(raw=raw, normalized=None, was_changed=False)

    if isinstance(raw, (datetime, date)):
        d = raw.date() if isinstance(raw, datetime) else raw
        return NormResult(raw=raw, normalized=d, was_changed=False)

    raw_str = str(raw).strip()

    for fmt in (
        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
        "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y",
        "%d/%m/%Y", "%d-%m-%Y",
    ):
        try:
            d = datetime.strptime(raw_str, fmt).date()
            return NormResult(raw=raw, normalized=d, was_changed=True)
        except ValueError:
            continue

    return NormResult(raw=raw, normalized=None, was_changed=False,
                      issues=[f"Could not parse date: {raw_str!r}"])


def estimate_event_date(order_desc: str | None, notes: str | None) -> NormResult:
    """Extract a date from the order description or technician notes text."""
    for text in [order_desc, notes]:
        if not text:
            continue
        match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", text)
        if match:
            result = normalize_date(match.group(1))
            if result.normalized:
                result.issues.append(f"Estimated from text: {match.group(0)}")
                return result
    return NormResult(raw=None, normalized=None, was_changed=False)


def normalize_float(raw: Any, field_name: str = "") -> NormResult:
    """Parse a numeric value, handling commas and whitespace."""
    if raw is None or str(raw).strip() in ("", "nan", "None"):
        return NormResult(raw=raw, normalized=None, was_changed=False)
    try:
        val = float(str(raw).replace(",", "").strip())
        issues = []
        if field_name == "order_cost" and val < 0:
            issues.append(f"Negative cost: {val}")
        if field_name == "order_cost" and val > 100000:
            issues.append(f"Unusually high cost: {val}")
        if field_name == "run_hours" and (val < 0 or val > 200000):
            issues.append(f"Run hours out of expected range: {val}")
        return NormResult(raw=raw, normalized=val, was_changed=False, issues=issues)
    except (ValueError, TypeError):
        return NormResult(raw=raw, normalized=None, was_changed=False,
                          issues=[f"Cannot parse as number: {raw!r}"])


def normalize_plant_code(raw: Any) -> NormResult:
    """Validate plant code is a 4-digit numeric string."""
    if raw is None or str(raw).strip() == "":
        return NormResult(raw=raw, normalized=None, was_changed=False)
    s = str(raw).strip()
    if re.match(r"^\d{4}$", s):
        return NormResult(raw=raw, normalized=s, was_changed=False)
    return NormResult(raw=raw, normalized=None, was_changed=True,
                      issues=[f"Invalid plant code (not 4-digit): {s!r}"])


def classify_event_category(description: str | None) -> str:
    """Classify a service event based on the order description text."""
    if not description:
        return "other"
    d = description.lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in d for kw in keywords):
            return category
    return "other"


def normalize_activity_type(raw: str | None) -> NormResult:
    """Map SAP activity type code to normalised label."""
    if not raw or str(raw).strip() == "":
        return NormResult(raw=raw, normalized=None, was_changed=False)
    s = str(raw).strip()
    mapped = ACTIVITY_TYPE_MAP.get(s)
    if mapped:
        return NormResult(raw=raw, normalized=mapped, was_changed=True)
    return NormResult(raw=raw, normalized=s, was_changed=False,
                      issues=[f"Unknown activity type code: {s!r}"])


def infer_issue_category(notes: str | None, description: str | None) -> Optional[tuple[str, str]]:
    """Derive (category_name, severity) from free-text fields."""
    combined = f"{notes or ''} {description or ''}".lower()
    for cat_name, keywords, severity in ISSUE_CATEGORY_RULES:
        if any(kw in combined for kw in keywords):
            return cat_name, severity
    return None


def normalize_equipment_number(raw: Any) -> NormResult:
    """Convert SAP equipment number (often a float) to a clean string."""
    if raw is None or str(raw).strip() in ("", "nan", "None"):
        return NormResult(raw=raw, normalized=None, was_changed=False)
    try:
        val = str(int(float(str(raw).strip())))
        return NormResult(raw=raw, normalized=val, was_changed=True)
    except (ValueError, TypeError):
        s = str(raw).strip()
        return NormResult(raw=raw, normalized=s, was_changed=False)


def clean_technician_notes(raw: str | None) -> NormResult:
    """Produce a cleaned version of technician notes for analytics.

    The original is always preserved as raw.  The cleaned version removes
    timestamps / author headers while keeping the substantive content.
    """
    if not raw or str(raw).strip() == "":
        return NormResult(raw=raw, normalized=None, was_changed=False)

    text = str(raw)
    lines = text.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.strip().lstrip("* ").strip()
        if not stripped:
            continue
        # Skip pure timestamp / author header lines
        if re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2}\s+\w+\s+\w+.*\(\w+\)$", stripped):
            continue
        if re.match(r"^\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2}\s+\w+\s+.*\(\w+\)$", stripped):
            continue
        cleaned_lines.append(stripped)

    cleaned = " ".join(cleaned_lines).strip()
    return NormResult(raw=raw, normalized=cleaned if cleaned else None, was_changed=True)


def extract_actions_from_notes(notes: str | None) -> list[dict]:
    """Parse free-text notes into structured action records.

    Returns list of dicts with keys: action_type_raw, component,
    description, technician_name_raw, technician_username, action_date,
    run_hours_at_action.
    """
    if not notes:
        return []

    actions: list[dict] = []
    entries = re.split(r"\n\*\s*", str(notes))

    for entry in entries:
        entry = entry.strip()
        if not entry or len(entry) < 10:
            continue

        tech_name = None
        tech_username = None
        name_match = re.search(r"(\w+(?:\s+\w+)?)\s*\((\w+)\)", entry)
        if name_match:
            tech_name = name_match.group(1).strip()
            tech_username = name_match.group(2).strip()

        run_hours = None
        hours_match = re.search(r"([\d,]+)\s*hrs?", entry, re.IGNORECASE)
        if hours_match:
            try:
                run_hours = float(hours_match.group(1).replace(",", ""))
            except ValueError:
                pass

        action_date = None
        date_match = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", entry)
        if date_match:
            result = normalize_date(date_match.group(1))
            action_date = result.normalized

        entry_lower = entry.lower()
        found_action = None
        for keyword, action_type in ACTION_KEYWORDS.items():
            if keyword in entry_lower:
                found_action = action_type
                break

        found_component = None
        for keyword, component in COMPONENT_KEYWORDS.items():
            if keyword in entry_lower:
                found_component = component
                break

        if found_action or found_component:
            actions.append({
                "action_type_raw": found_action or "general",
                "component": found_component,
                "description": entry[:500],
                "technician_name_raw": tech_name,
                "technician_username": tech_username,
                "action_date": action_date,
                "run_hours_at_action": run_hours,
            })

    return actions


def extract_notes_entries(raw_notes: str | None) -> list[dict]:
    """Break technician notes into individual structured note entries.

    Returns list of dicts with: raw_text, author_name, author_username,
    note_date, note_type.
    """
    if not raw_notes:
        return []

    entries = re.split(r"\n\*\s*", str(raw_notes))
    results: list[dict] = []

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue

        author_name = None
        author_username = None
        note_date = None

        header_match = re.match(
            r"(\d{2}[/-]\d{2}[/-]\d{4})\s+(\d{2}:\d{2}:\d{2})\s+\w+\s+([\w\s]+?)\s*\((\w+)\)",
            entry,
        )
        if header_match:
            date_result = normalize_date(header_match.group(1))
            if date_result.normalized:
                try:
                    time_parts = header_match.group(2).split(":")
                    note_date = datetime(
                        date_result.normalized.year,
                        date_result.normalized.month,
                        date_result.normalized.day,
                        int(time_parts[0]), int(time_parts[1]), int(time_parts[2]),
                    )
                except (ValueError, IndexError):
                    note_date = datetime.combine(date_result.normalized, datetime.min.time())
            author_name = header_match.group(3).strip()
            author_username = header_match.group(4).strip()

        note_type = "review_comment" if header_match else "technician_note"

        results.append({
            "raw_text": entry,
            "author_name": author_name,
            "author_username": author_username,
            "note_date": note_date,
            "note_type": note_type,
        })

    return results
