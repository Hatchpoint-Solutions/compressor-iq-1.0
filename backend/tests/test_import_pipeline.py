"""Integration tests for the full import pipeline."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import (
    Compressor,
    ImportBatch,
    ImportIssueLog,
    RawServiceRow,
    ServiceEvent,
    ServiceEventAction,
    ServiceEventNote,
    Site,
    Technician,
)


@pytest.fixture
def fresh_db():
    """Create a fresh SQLite in-memory database for pipeline tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestFullPipeline:
    def test_import_creates_records(self, fresh_db, sample_xlsx):
        from app.services.ingestion.import_service import run_import

        batch, report = run_import(fresh_db, file_paths=[sample_xlsx])

        assert batch.status == "completed"
        assert report.files_processed == 1
        assert report.rows_scanned == 3
        assert report.events_created == 3

        events = fresh_db.query(ServiceEvent).all()
        assert len(events) == 3

        compressors = fresh_db.query(Compressor).all()
        assert len(compressors) == 1
        assert compressors[0].unit_id == "MC6068"

        sites = fresh_db.query(Site).all()
        assert len(sites) >= 1

    def test_idempotent_reimport(self, fresh_db, sample_xlsx):
        """Re-importing the same file should not create duplicate events."""
        from app.services.ingestion.import_service import run_import

        batch1, report1 = run_import(fresh_db, file_paths=[sample_xlsx])
        assert report1.events_created == 3

        batch2, report2 = run_import(fresh_db, file_paths=[sample_xlsx])
        assert report2.events_created == 0
        # File hash check prevents reprocessing
        assert report2.rows_scanned == 0

        total_events = fresh_db.query(ServiceEvent).count()
        assert total_events == 3

    def test_raw_rows_preserved(self, fresh_db, sample_xlsx):
        from app.services.ingestion.import_service import run_import

        run_import(fresh_db, file_paths=[sample_xlsx])

        raw_rows = fresh_db.query(RawServiceRow).all()
        assert len(raw_rows) == 3
        for rr in raw_rows:
            assert rr.raw_data_json is not None
            assert rr.mapped_data_json is not None
            assert rr.normalization_status == "imported"

    def test_issues_logged(self, fresh_db, sample_xlsx):
        from app.services.ingestion.import_service import run_import

        batch, report = run_import(fresh_db, file_paths=[sample_xlsx])

        issues = fresh_db.query(ImportIssueLog).filter(
            ImportIssueLog.batch_id == batch.id
        ).all()
        # Row 1 has no Reading Date → should log a warning
        missing_date_issues = [i for i in issues if i.issue_type == "missing_reading_date"]
        assert len(missing_date_issues) >= 1

    def test_actions_extracted(self, fresh_db, sample_xlsx):
        from app.services.ingestion.import_service import run_import

        run_import(fresh_db, file_paths=[sample_xlsx])

        actions = fresh_db.query(ServiceEventAction).all()
        assert len(actions) > 0
        assert any(a.action_type_raw is not None for a in actions)

    def test_notes_extracted(self, fresh_db, sample_xlsx):
        from app.services.ingestion.import_service import run_import

        run_import(fresh_db, file_paths=[sample_xlsx])

        notes = fresh_db.query(ServiceEventNote).all()
        assert len(notes) > 0

    def test_event_traceability(self, fresh_db, sample_xlsx):
        """Every event should link back to its batch, file, and raw row."""
        from app.services.ingestion.import_service import run_import

        batch, _ = run_import(fresh_db, file_paths=[sample_xlsx])

        events = fresh_db.query(ServiceEvent).all()
        for evt in events:
            assert evt.import_batch_id == batch.id
            assert evt.import_file_id is not None
            assert evt.raw_row_id is not None

    def test_batch_summary_populated(self, fresh_db, sample_xlsx):
        from app.services.ingestion.import_service import run_import

        batch, report = run_import(fresh_db, file_paths=[sample_xlsx])

        assert batch.total_rows_scanned > 0
        assert batch.total_rows_imported > 0
        assert batch.summary_json is not None
        assert "events_created" in batch.summary_json
