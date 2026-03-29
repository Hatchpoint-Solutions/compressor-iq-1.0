"""Ingestion pipeline package.

Stages:
  1. file_discovery   – scan directory for spreadsheet/CSV files
  2. workbook_reader  – open workbooks, extract sheet metadata + raw rows
  3. source_mapper    – map source column names to internal field names
  4. normalizer       – clean / normalize values (dates, IDs, actions, etc.)
  5. validator        – apply business rules and data quality checks
  6. issue_logger     – persist data quality issues
  7. deduplication    – detect and handle duplicate rows
  8. import_service   – orchestrate the full pipeline
"""
