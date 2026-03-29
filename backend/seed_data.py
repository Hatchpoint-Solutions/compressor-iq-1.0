"""Seed the database from the initial Excel file via the new ingestion pipeline.

Usage:
    cd backend
    python seed_data.py

This will:
1. Create all database tables
2. Run the full ingestion pipeline against the MC6068 spreadsheet
3. Print summary statistics and the import report
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import Base, SessionLocal, engine
from app.models import (
    Compressor,
    ImportBatch,
    ImportIssueLog,
    IssueCategory,
    ServiceEvent,
    ServiceEventAction,
    ServiceEventNote,
    Site,
    Technician,
)


def main():
    project_root = os.path.dirname(os.path.dirname(__file__))
    excel_path = os.path.join(project_root, "Unit MC6068 Maintenance.xlsx")

    if not os.path.exists(excel_path):
        print(f"ERROR: Excel file not found at {excel_path}")
        sys.exit(1)

    print(f"Found data file: {excel_path}")
    os.makedirs("data/uploads", exist_ok=True)

    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing = db.query(ServiceEvent).count()
        if existing > 0:
            print(f"Database already has {existing} events. Skipping seed.")
            _print_stats(db)
            return

        print("Running ingestion pipeline...")
        from app.services.ingestion.import_service import run_import

        batch, report = run_import(
            db,
            file_paths=[excel_path],
            initiated_by="seed_data.py",
        )

        print("\n" + "=" * 60)
        print("IMPORT REPORT")
        print("=" * 60)
        for key, value in report.to_dict().items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k2, v2 in value.items():
                    print(f"    {k2}: {v2}")
            else:
                print(f"  {key}: {value}")

        _print_stats(db)
        print("\nSeed completed successfully!")

    finally:
        db.close()


def _print_stats(db):
    from sqlalchemy import func

    print("\n" + "=" * 60)
    print("DATABASE STATISTICS")
    print("=" * 60)
    print(f"  Import Batches:      {db.query(ImportBatch).count()}")
    print(f"  Compressors:         {db.query(Compressor).count()}")
    print(f"  Sites:               {db.query(Site).count()}")
    print(f"  Technicians:         {db.query(Technician).count()}")
    print(f"  Service Events:      {db.query(ServiceEvent).count()}")
    print(f"  Event Actions:       {db.query(ServiceEventAction).count()}")
    print(f"  Event Notes:         {db.query(ServiceEventNote).count()}")
    print(f"  Issue Categories:    {db.query(IssueCategory).count()}")
    print(f"  Import Issues:       {db.query(ImportIssueLog).count()}")

    print("\nEvents by category:")
    for row in (
        db.query(ServiceEvent.event_category, func.count(ServiceEvent.id))
        .group_by(ServiceEvent.event_category)
        .order_by(func.count(ServiceEvent.id).desc())
        .all()
    ):
        print(f"    {row[0]}: {row[1]}")

    print("\nIssues by severity:")
    for row in (
        db.query(ImportIssueLog.severity, func.count(ImportIssueLog.id))
        .group_by(ImportIssueLog.severity)
        .order_by(ImportIssueLog.severity)
        .all()
    ):
        print(f"    {row[0]}: {row[1]}")

    print("\nIssues by type (top 10):")
    for row in (
        db.query(ImportIssueLog.issue_type, func.count(ImportIssueLog.id))
        .group_by(ImportIssueLog.issue_type)
        .order_by(func.count(ImportIssueLog.id).desc())
        .limit(10)
        .all()
    ):
        print(f"    {row[0]}: {row[1]}")


if __name__ == "__main__":
    main()
