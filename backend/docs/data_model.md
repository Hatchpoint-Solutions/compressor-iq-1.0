# Data Model

## Overview

The CompressorIQ data model is organized into four logical zones:

1. **Import / Audit Zone** — raw data preservation and traceability
2. **Master / Reference Zone** — normalized lookup entities
3. **Core Event Zone** — normalized service events and related data
4. **Analytics Zone** — recommendations, workflows, and feedback (future extension)

Every normalized record can be traced back to its original source file, sheet, and row.

---

## Zone A: Import / Audit Tables

### `import_batches`

One logical import run that may cover multiple files.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| batch_key | VARCHAR(128) | Yes | Idempotency key (hash of file set) |
| status | VARCHAR(20) | No | pending / processing / completed / failed |
| source_directory | VARCHAR(1000) | Yes | Root directory scanned |
| initiated_by | VARCHAR(200) | Yes | User or system that triggered import |
| total_files | INT | No | Default 0 |
| total_rows_scanned | INT | No | Default 0 |
| total_rows_imported | INT | No | Default 0 |
| total_rows_skipped | INT | No | Default 0 |
| total_rows_errored | INT | No | Default 0 |
| total_issues | INT | No | Default 0 |
| summary_json | JSON | Yes | Full import report as structured data |
| started_at | TIMESTAMP | No | Auto-set |
| completed_at | TIMESTAMP | Yes | Set on completion |

### `import_files`

Each file discovered and processed within a batch.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| batch_id | UUID (FK → import_batches) | No | |
| file_name | VARCHAR(500) | No | Original filename |
| file_path | VARCHAR(1000) | No | Full filesystem path |
| file_hash | VARCHAR(128) | Yes | SHA-256 of file contents (dedup key) |
| file_size_bytes | INT | Yes | |
| file_type | VARCHAR(20) | No | xlsx / xls / csv / tsv |
| status | VARCHAR(20) | No | discovered / processing / completed / failed |
| row_count | INT | Yes | Total rows across all sheets |
| sheet_count | INT | Yes | |
| discovered_at | TIMESTAMP | No | Auto-set |
| processed_at | TIMESTAMP | Yes | |

### `import_sheets`

Metadata for one worksheet within an import file.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| file_id | UUID (FK → import_files) | No | |
| sheet_name | VARCHAR(200) | No | |
| sheet_index | INT | No | 0-based |
| row_count | INT | No | |
| column_count | INT | No | |
| column_names_json | JSON | Yes | List of column headers |
| status | VARCHAR(20) | No | pending / processing / completed |

### `raw_service_rows`

Verbatim preservation of every source row. This is the raw-data archive.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| sheet_id | UUID (FK → import_sheets) | No | |
| row_number | INT | No | 1-based position in source sheet |
| row_hash | VARCHAR(128) | No | SHA-256 fingerprint of row content |
| raw_data_json | JSON | No | All columns as key-value pairs |
| mapped_data_json | JSON | Yes | After column-name mapping |
| normalization_status | VARCHAR(20) | No | pending / mapped / normalized / validated / imported / skipped / errored |
| normalized_event_id | UUID (FK → service_events) | Yes | Link to created event |
| created_at | TIMESTAMP | No | |

### `import_issue_log`

Data quality issues detected during import.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| batch_id | UUID (FK → import_batches) | No | |
| file_id | UUID (FK → import_files) | Yes | |
| sheet_id | UUID (FK → import_sheets) | Yes | |
| raw_row_id | UUID (FK → raw_service_rows) | Yes | |
| row_number | INT | Yes | |
| severity | VARCHAR(10) | No | info / warning / error |
| issue_type | VARCHAR(100) | No | Coded issue identifier |
| issue_description | TEXT | No | Human-readable description |
| source_column | VARCHAR(200) | Yes | Which source column had the issue |
| source_value | TEXT | Yes | The problematic value |
| suggested_fix | TEXT | Yes | |
| created_at | TIMESTAMP | No | |

---

## Zone B: Master / Reference Tables

### `compressors`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| unit_id | VARCHAR(50) | No | Canonical normalized ID (e.g. MC6068). UNIQUE |
| raw_source_unit_ids | JSON | Yes | All original variants observed |
| equipment_number | VARCHAR(50) | Yes | SAP equipment number |
| compressor_type | VARCHAR(50) | Yes | |
| manufacturer | VARCHAR(100) | Yes | |
| model | VARCHAR(100) | Yes | |
| status | VARCHAR(20) | No | Default 'active' |
| current_run_hours | FLOAT | Yes | Latest known run hours |
| first_seen_date | DATE | Yes | Earliest event date |
| site_id | UUID (FK → sites) | Yes | Current site assignment |
| created_at | TIMESTAMP | No | |
| updated_at | TIMESTAMP | No | |

### `sites`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| plant_code | VARCHAR(20) | No | SAP plant code. UNIQUE with customer_name |
| customer_name | VARCHAR(200) | No | |
| name | VARCHAR(200) | Yes | Friendly site name |
| region | VARCHAR(100) | Yes | |
| raw_source_names | JSON | Yes | Customer name variants observed |
| created_at | TIMESTAMP | No | |
| updated_at | TIMESTAMP | No | |

### `technicians`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| name | VARCHAR(200) | No | Title-cased canonical name. UNIQUE |
| raw_source_names | JSON | Yes | All name variants observed |
| username | VARCHAR(50) | Yes | SAP username (e.g. MBURNETT). UNIQUE |
| first_seen_date | DATE | Yes | |
| event_count | INT | No | Default 0 |
| created_at | TIMESTAMP | No | |

### `maintenance_action_types`

Controlled vocabulary for action types.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| code | VARCHAR(50) | No | UNIQUE. E.g. OIL_CHANGE |
| label | VARCHAR(200) | No | Human-readable label |
| category | VARCHAR(50) | Yes | Grouping |
| source_patterns | JSON | Yes | Free-text patterns that map here |
| created_at | TIMESTAMP | No | |

### `issue_categories`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| name | VARCHAR(100) | No | UNIQUE. E.g. detonation, leak |
| description | TEXT | Yes | |
| severity_default | VARCHAR(20) | No | Default 'medium' |
| detection_keywords | JSON | Yes | Auto-detection keywords |
| created_at | TIMESTAMP | No | |

### `service_outcome_types` (future)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| code | VARCHAR(50) | No | UNIQUE |
| label | VARCHAR(200) | No | |
| is_resolved | BOOLEAN | No | Default TRUE |
| created_at | TIMESTAMP | No | |

---

## Zone C: Core Event Tables

### `service_events`

The central fact table — one row per maintenance work order.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| compressor_id | UUID (FK → compressors) | No | |
| order_number | VARCHAR(50) | No | UNIQUE. SAP order number |
| order_description | VARCHAR(500) | Yes | Parsed description portion |
| raw_order_and_description | TEXT | Yes | Original compound field value |
| event_date | DATE | Yes | |
| event_date_source | VARCHAR(50) | Yes | reading_date / estimated_from_text |
| event_date_estimated | BOOLEAN | No | Default FALSE |
| event_category | VARCHAR(100) | Yes | Classified category |
| maintenance_activity_type_raw | VARCHAR(200) | Yes | Original SAP code |
| maintenance_activity_type | VARCHAR(100) | Yes | Normalized label |
| order_type | VARCHAR(20) | Yes | ZNS1 / ZNS6 |
| order_status | VARCHAR(50) | Yes | TECO / Closed / Released / Created |
| user_status | VARCHAR(50) | Yes | |
| technician_notes_raw | TEXT | Yes | Original verbatim |
| technician_notes_clean | TEXT | Yes | Cleaned for analytics |
| run_hours_at_event | FLOAT | Yes | |
| order_cost | FLOAT | Yes | |
| order_revenue | FLOAT | Yes | |
| currency | VARCHAR(10) | No | Default 'USD' |
| plant_code | VARCHAR(20) | Yes | |
| customer_name | VARCHAR(200) | Yes | |
| issue_category_id | UUID (FK → issue_categories) | Yes | |
| import_batch_id | UUID (FK → import_batches) | Yes | Lineage |
| import_file_id | UUID (FK → import_files) | Yes | Lineage |
| raw_row_id | UUID (FK → raw_service_rows) | Yes | Lineage |
| created_at | TIMESTAMP | No | |
| updated_at | TIMESTAMP | No | |

### `service_event_actions`

Individual actions parsed from technician notes.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| service_event_id | UUID (FK → service_events) | No | |
| action_type_id | UUID (FK → maintenance_action_types) | Yes | |
| action_type_raw | VARCHAR(100) | Yes | Original action text |
| component | VARCHAR(200) | Yes | Affected component |
| description | TEXT | Yes | Full note entry |
| technician_id | UUID (FK → technicians) | Yes | |
| technician_name_raw | VARCHAR(200) | Yes | Original name |
| action_date | DATE | Yes | |
| run_hours_at_action | FLOAT | Yes | |
| sequence_number | INT | No | Default 1 |
| created_at | TIMESTAMP | No | |

### `service_event_notes`

Structured note entries parsed from review comments.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| service_event_id | UUID (FK → service_events) | No | |
| note_type | VARCHAR(30) | No | technician_note / review_comment / system_note |
| raw_text | TEXT | No | Verbatim note text |
| cleaned_text | TEXT | Yes | |
| author_name | VARCHAR(200) | Yes | |
| author_username | VARCHAR(50) | Yes | |
| note_date | TIMESTAMP | Yes | |
| sequence_number | INT | No | Default 1 |

### `service_event_measurements`

Structured numeric data extracted from events.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | UUID (PK) | No | |
| service_event_id | UUID (FK → service_events) | No | |
| measurement_type | VARCHAR(50) | No | run_hours / cost / pressure / temperature |
| value | FLOAT | No | |
| unit | VARCHAR(20) | Yes | hrs / USD / psi / F |
| measured_at | DATE | Yes | |
| source | VARCHAR(50) | Yes | reading_date / extracted_from_notes |

---

## Zone D: Analytics Tables (Future Extension)

- `recommendations` — generated maintenance recommendations
- `workflow_steps` — step-by-step instructions
- `similar_cases` — historical case matching
- `feedback_outcomes` — technician feedback capture

These tables are defined in the schema but are not populated by the ingestion pipeline.

---

## Entity Relationship Diagram (Simplified)

```
import_batches 1──* import_files 1──* import_sheets 1──* raw_service_rows
     │                                                          │
     └──────────────── import_issue_log ────────────────────────┘
                                                                │
sites 1──* compressors 1──* service_events ────────────── raw_service_rows
                                 │
                                 ├──* service_event_actions ──── technicians
                                 ├──* service_event_notes
                                 ├──* service_event_measurements
                                 └──1 issue_categories
```
