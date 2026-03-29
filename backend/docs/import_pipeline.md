# Import Pipeline

## Overview

The ingestion pipeline processes spreadsheet and CSV files through 10 sequential stages. It is designed for repeatability, auditability, and safety.

## Pipeline Stages

### Stage 1: File Discovery (`file_discovery.py`)

- Recursively scans a directory for `.xlsx`, `.xls`, `.csv`, `.tsv` files
- Skips known non-data directories (node_modules, .git, __pycache__, etc.)
- Returns a list of `DiscoveredFile` objects with path, type, and size

### Stage 2: Batch Registration (`import_service.py`)

- Creates an `ImportBatch` record to track the entire run
- Creates an `ImportFile` record for each discovered file
- Computes SHA-256 file hash for deduplication
- **If a file with the same hash already exists**, it is skipped with an info-level issue log

### Stage 3: Workbook Reading (`workbook_reader.py`)

- Opens each file using pandas/openpyxl
- Enumerates all sheets (or treats CSV as a single sheet)
- Reads all rows as strings to preserve raw values
- Creates `ImportSheet` records with column metadata

### Stage 4: Raw Row Persistence (`import_service.py`)

- Each source row is stored in `raw_service_rows` as JSON
- A SHA-256 fingerprint is computed from the row content
- **If a row with the same fingerprint already exists**, it is skipped (duplicate detection)
- Both `raw_data_json` (original column names) and `mapped_data_json` (target field names) are preserved

### Stage 5: Column Mapping (`source_mapper.py`)

- Maps source column names (e.g. "Order & Description") to target field names (e.g. "order_and_description")
- Ignores columns known to be empty (GM %, Days to Inv., etc.)
- Preserves the mapping configuration in `COLUMN_MAPPINGS` for documentation and audit

### Stage 6: Value Normalization (`normalizer.py`)

Each value goes through type-specific normalization:

- **Unit IDs**: strip whitespace, uppercase, extract MC/EF pattern, map EF→MC prefix
- **Dates**: try multiple formats (ISO, US, EU), log failures
- **Floats**: remove commas, validate ranges
- **Plant codes**: validate 4-digit numeric pattern
- **Activity types**: map SAP codes to canonical labels
- **Event categories**: classify from description text using keyword rules
- **Technician notes**: preserve raw, produce cleaned version stripping timestamps/headers
- **Actions**: parse from free-text into structured records with action type, component, technician, date

Every normalization returns a `NormResult` with original value, normalized value, change flag, and issues.

### Stage 7: Business Rule Validation (`validator.py`)

Applies rules with three severity levels:

- **Error** (blocks import): missing Order & Description, missing machine ID, negative run hours, invalid plant code
- **Warning** (allows import with flag): missing Reading Date, negative cost, extreme run hours
- **Info** (informational): empty technician notes, high cost

### Stage 8: Normalized Persistence (`import_service.py`)

For each valid row:
1. Get-or-create **Compressor** (by normalized unit_id)
2. Get-or-create **Site** (by plant_code + customer_name)
3. Get-or-create **Technician** (by canonical name or username)
4. Create **ServiceEvent** with full lineage (batch_id, file_id, raw_row_id)
5. Create **ServiceEventActions** parsed from notes
6. Create **ServiceEventNotes** (structured note entries)
7. Create **ServiceEventMeasurements** (run hours, cost as structured data)
8. Infer and assign **IssueCategory** for corrective events

### Stage 9: Issue Logging (`issue_logger.py`)

- All validation issues are persisted to `import_issue_log`
- Each issue links to batch, file, sheet, and raw row for full traceability
- Custom issues (duplicate file, duplicate row, normalization exception) are also logged

### Stage 10: Import Report

The pipeline returns an `ImportReport` with:
- Files/sheets/rows processed
- Records created (events, actions, notes, measurements)
- Compressors/sites/technicians created
- Issues by severity and type
- Full summary stored as JSON in the batch record

## Idempotency

The pipeline uses two deduplication mechanisms:

1. **File-level**: SHA-256 hash of file contents prevents reprocessing the same file
2. **Row-level**: SHA-256 fingerprint of row content prevents duplicate raw rows
3. **Event-level**: Order number uniqueness prevents duplicate service events

Re-running the import against the same files is safe and will produce no duplicates.

## Error Handling

- Row-level errors are caught and logged without aborting the batch
- The batch status reflects overall success/failure
- Individual rows are marked with their normalization status (imported / skipped / errored)
- The summary JSON contains all counters for programmatic access
