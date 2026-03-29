# Source-to-Target Mapping

## Source File: Unit MC6068 Maintenance.xlsx

**Sheet**: Export
**Rows**: 305 (303 data + 1 header + 1 metadata footer)
**Columns**: 19

## Column Mapping

| # | Source Column | Target Field | Required | Transform | Example Values |
|---|--------------|-------------|----------|-----------|---------------|
| 0 | Plant | plant_code | No | Strip; validate 4-digit numeric. Metadata rows (non-4-digit) are rejected. | 1031, 1032, 1030, 1037 |
| 1 | Order & Description | order_and_description → order_number + unit_id + order_description | **Yes** | Split on ' - ' into 3 parts. First = order number, second = unit ID (raw), third = description. | "4113904 - MC6068 - JANUARY 2020 CALLOUTS" |
| 2 | Customer Name | customer_name | No | Strip; preserve as-is. | "EOG Resources Inc", "ConocoPhillips Co" |
| 3 | Equipment | equipment_number | No | Convert float to int string (500021946.0 → "500021946") | 500021946 |
| 4 | Type | order_type | No | Strip; uppercase. | ZNS1, ZNS6 |
| 5 | Order Review Comments | technician_notes (raw + clean) | No | Preserve verbatim as `technician_notes_raw`. Clean version strips timestamp headers. Parse into structured actions and notes. | Rich free-text with embedded dates, names, hours |
| 6 | Order Status | order_status | No | Strip; uppercase. | TECO, Closed, Released, Created |
| 7 | User Status | user_status | No | Strip; uppercase. | SMOK, CRTD, SPCC |
| 8 | Maintenance Activity Type | maintenance_activity_type_raw + maintenance_activity_type | No | Preserve raw. Map code: ZUR→unscheduled_repair, ZPM→preventive_maintenance, ZPR→preservation | "ZUR - Unscheduled Repair -Mechanical" → "unscheduled_repair" |
| 9 | Order Cost | order_cost | No | Parse float. Log if negative or >50K. | -252.35 to 24,697.98 |
| 10 | Order Revenue | order_revenue | No | Parse float. Always 0 in current data. | 0 |
| 11 | Currency | currency | No | Strip; uppercase; default USD. | USD |
| 17 | Run Hours | run_hours → run_hours_at_event + measurement | No | Parse float. Validate range 0-200,000. Also creates a ServiceEventMeasurement record. | 23,847 to 62,328 |
| 18 | Reading Date | reading_date → event_date | No | Parse datetime. If null, estimate from description/notes. Mark estimated dates with `event_date_estimated=true`. | 2021-08-08 to 2026-03-11 |

## Ignored Columns (No Useful Data)

| Source Column | Reason |
|--------------|--------|
| GM % | 100% null |
| Days to Inv. | 100% null |
| Category | Always "No Group" |
| Sub-Orders | 100% null |
| Lead Order | 100% null |

## Derived Fields

| Target Field | Derivation |
|-------------|------------|
| event_category | Classified from order_description using keyword rules (corrective, preventive_maintenance, emissions_inspection, etc.) |
| event_date_source | "reading_date" if from Reading Date column; "estimated_from_text" if estimated |
| event_date_estimated | Boolean flag when date was estimated |
| issue_category_id | Inferred from technician_notes for corrective events using keyword matching |
| technician_notes_clean | Cleaned version of notes with timestamp/author headers removed |

## Action Extraction from Technician Notes

The notes field is parsed to extract structured actions:

| Extracted Field | Pattern | Example |
|----------------|---------|---------|
| action_type_raw | Keyword match: replaced, installed, adjusted, inspected, cleaned, etc. | "replaced" from "REPLACED AIR FILTERS" |
| component | Keyword match: spark_plug, filter, oil, valve, etc. | "air_filter" from "BLEW OUT AIR FILTERS" |
| technician_name_raw | Regex: `Name (USERNAME)` | "Meagan Burnett" from "Meagan Burnett (MBURNETT)" |
| action_date | Regex: `MM/DD/YYYY` or `MM-DD-YYYY` | 01/02/2020 |
| run_hours_at_action | Regex: `N,NNN hrs` | 18,671 from "@ 18,671 hrs" |

## Event Category Classification Rules

| Category | Trigger Keywords |
|----------|-----------------|
| corrective | corrective, callout, callouts, non-pm, npm |
| preventive_maintenance | pm-1, pm-2, routine, annual, semi |
| emissions_inspection | emission |
| oil_sampling | oil sample, engine oil |
| coolant_sampling | coolant sample |
| packing_maintenance | packing |
| valve_inspection | psv, prv |
| preservation | preservation |
| unit_wash | wash |
| startup | start up, start-up, new set |
| telemetry | telemetry, reliability |
| other | (no keyword match) |

## Issue Category Inference Rules

Applied to corrective events only, using technician_notes + description:

| Category | Keywords | Default Severity |
|----------|----------|-----------------|
| detonation | detonation, detination, detnation | high |
| leak | leak | medium |
| pressure_abnormality | pressure, suction, discharge | medium |
| fuel_system | fuel, btu | medium |
| valve_failure | valve | medium |
| cooling_system | coolant, temperature, water | medium |
| electrical | wiring, sensor, scanner, panel | medium |
| lubrication | oil | medium |
| filter_maintenance | filter | low |
| shutdown | shutdown, shut down, down on | high |
| vibration_noise | vibration, noise | medium |
| seal_gasket | seal, gasket, packing | medium |
