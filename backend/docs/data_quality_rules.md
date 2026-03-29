# Data Quality Rules

## Overview

The data quality framework validates every row before it enters the normalized tables. Issues are logged at three severity levels:

- **Error**: Prevents the row from being imported. The row remains in `raw_service_rows` with status `errored`.
- **Warning**: Row is imported but flagged. May need manual review.
- **Info**: Informational — no action required but logged for completeness.

## Validation Rules

### Error-Level Rules (Block Import)

| Rule ID | Field | Condition | Description |
|---------|-------|-----------|-------------|
| missing_order_description | Order & Description | Empty or null | Cannot derive order number or unit ID |
| missing_machine_id | Order & Description | Cannot extract unit ID from compound field | Compound field format must be 'ORDER# - UNIT_ID - DESC' |
| negative_run_hours | Run Hours | Value < 0 | Invalid measurement |
| invalid_plant_code | Plant | Length > 10 characters | Likely a metadata/footer row containing SAP filter text |

### Warning-Level Rules (Import with Flag)

| Rule ID | Field | Condition | Description |
|---------|-------|-----------|-------------|
| missing_reading_date | Reading Date | Null or empty | Date will be estimated from description/notes text |
| negative_order_cost | Order Cost | Value < 0 | May be a credit/refund or data error |
| extreme_run_hours | Run Hours | Value > 200,000 | Exceeds expected lifetime range |
| invalid_order_cost | Order Cost | Cannot parse as number | Non-numeric value |
| invalid_run_hours | Run Hours | Cannot parse as number | Non-numeric value |

### Info-Level Rules (Logged Only)

| Rule ID | Field | Condition | Description |
|---------|-------|-----------|-------------|
| empty_technician_notes | Order Review Comments | Empty or null | No actions can be extracted |
| high_order_cost | Order Cost | Value > 50,000 | Unusually high — worth reviewing |
| duplicate_file | File | SHA-256 match with existing import | File already processed |
| duplicate_row | Row | Content fingerprint match | Row already imported |
| duplicate_order_number | Order Number | Already exists in service_events | Order already normalized |

## Normalization Quality Checks

Beyond validation, the normalizer logs issues when:

- A date string cannot be parsed despite multiple format attempts
- A unit ID does not match the expected MC/EF pattern
- An unknown activity type code is encountered
- An equipment number cannot be parsed as a number
- A negative or extreme numeric value is encountered

## Issue Log Schema

Every issue is persisted with full traceability:

```
import_issue_log:
  - batch_id   → which import run
  - file_id    → which file
  - sheet_id   → which sheet
  - raw_row_id → which raw row
  - row_number → 1-based position in source
  - severity   → info / warning / error
  - issue_type → coded identifier
  - issue_description → human-readable text
  - source_column → which spreadsheet column
  - source_value → the problematic value
  - suggested_fix → remediation guidance
```

## Querying Issues

Issues can be queried via the API:

```
GET /api/imports/{batch_id}/issues
GET /api/imports/{batch_id}/issues?severity=error
GET /api/imports/{batch_id}/issues?issue_type=missing_reading_date
```

## Known Data Quality Observations

Based on the MC6068 dataset:

| Observation | Impact | Handling |
|-------------|--------|----------|
| 52.8% of rows lack Reading Date | Event dates must be estimated | Dates estimated from description/notes text, flagged with `event_date_estimated=true` |
| 1 metadata footer row in Plant column | Would create invalid records | Detected by `invalid_plant_code` rule and blocked |
| Some technician notes have misspellings (detination, detnation) | Could miss issue classification | Misspelling variants included in keyword rules |
| 36% of rows lack Order Cost | Cost analytics incomplete | Null costs are preserved, not defaulted |
| 5 empty columns | No useful information | Excluded from mapping (`IGNORED_COLUMNS`) |

## Future Enhancements

- Cross-row validation (e.g. run hours should be monotonically increasing for a compressor)
- Configurable rules via database or config file (not just code)
- Anomaly detection on numeric fields
- Automated suggested fixes with confidence scores
