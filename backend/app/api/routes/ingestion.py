"""File upload and ingestion endpoints.

POST /api/ingestion/upload   — upload a spreadsheet and run the import pipeline
GET  /api/ingestion/uploads  — list previous upload/import batches
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.import_models import ImportBatch, ImportFile

router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}


def _preview_columns(file_path: str) -> list[str] | None:
    """Read column names from the first sheet of a file without processing all rows."""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        import pandas as pd
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, nrows=0)
        elif ext in (".csv", ".tsv"):
            sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(file_path, nrows=0, sep=sep)
        else:
            return None
        return [str(c).strip() for c in df.columns if str(c).strip()]
    except Exception:
        return None


@router.post("/upload")
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    dest_path = os.path.join(upload_dir, safe_name)

    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as exc:
        logger.exception("Failed to save uploaded file")
        raise HTTPException(status_code=500, detail="Failed to save file.") from exc

    abs_path = os.path.abspath(dest_path)

    columns = _preview_columns(abs_path)
    if columns is not None:
        from app.services.ingestion.source_mapper import validate_column_compatibility
        matched, missing_required = validate_column_compatibility(columns)
        if not matched:
            return {
                "id": str(uuid.uuid4()),
                "filename": file.filename,
                "upload_date": datetime.utcnow().isoformat(),
                "status": "failed",
                "records_imported": 0,
                "error_message": (
                    f"No recognized columns found. "
                    f"Found columns: {', '.join(columns[:10])}. "
                    f"Expected SAP-style export with columns like: "
                    f"Plant, Order & Description, Customer Name, Equipment, etc."
                ),
            }
        if missing_required:
            return {
                "id": str(uuid.uuid4()),
                "filename": file.filename,
                "upload_date": datetime.utcnow().isoformat(),
                "status": "failed",
                "records_imported": 0,
                "error_message": (
                    f"Missing required column(s): {', '.join(missing_required)}. "
                    f"Matched {len(matched)} of the expected columns: {', '.join(matched[:8])}."
                ),
            }

    try:
        from app.services.ingestion.import_service import run_import

        batch, report = run_import(
            db,
            file_paths=[abs_path],
            initiated_by="file_upload",
        )

        return {
            "id": batch.id,
            "filename": file.filename,
            "upload_date": batch.started_at.isoformat() if batch.started_at else datetime.utcnow().isoformat(),
            "status": "completed" if batch.status == "completed" else batch.status,
            "records_imported": report.rows_imported,
            "error_message": None,
        }
    except Exception as exc:
        logger.exception("Import pipeline failed for uploaded file")
        return {
            "id": str(uuid.uuid4()),
            "filename": file.filename,
            "upload_date": datetime.utcnow().isoformat(),
            "status": "failed",
            "records_imported": 0,
            "error_message": str(exc),
        }


@router.get("/uploads")
def list_uploads(db: Session = Depends(get_db)):
    batches = (
        db.query(ImportBatch)
        .order_by(ImportBatch.started_at.desc().nullslast())
        .limit(50)
        .all()
    )

    results = []
    for batch in batches:
        files = db.query(ImportFile).filter(ImportFile.batch_id == batch.id).all()
        filename = files[0].file_name if files else "unknown"
        results.append({
            "id": batch.id,
            "filename": filename,
            "upload_date": batch.started_at.isoformat() if batch.started_at else None,
            "status": batch.status or "completed",
            "records_imported": batch.total_rows_imported,
            "error_message": None,
        })

    return results
