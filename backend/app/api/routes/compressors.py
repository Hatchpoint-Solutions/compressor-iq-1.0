"""Compressor (asset) endpoints.

GET  /compressors            — list all compressors
GET  /compressors/{id}       — detail with stats
GET  /compressors/{id}/timeline — service event timeline
GET  /compressors/{id}/issues   — issue frequency analysis
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.master_models import Compressor
from app.models.event_models import ServiceEvent
from app.schemas.compressor_schemas import (
    CompressorDetail,
    CompressorIssueFrequency,
    CompressorResponse,
)
from app.schemas.event_schemas import ServiceEventListItem


router = APIRouter(prefix="/api/compressors", tags=["compressors"])


@router.get("/", response_model=list[CompressorResponse])
def list_compressors(db: Session = Depends(get_db)):
    return db.query(Compressor).order_by(Compressor.unit_id).all()


@router.get("/{compressor_id}", response_model=CompressorDetail)
def get_compressor(compressor_id: str, db: Session = Depends(get_db)):
    comp = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Compressor not found")

    total = (
        db.query(func.count(ServiceEvent.id))
        .filter(ServiceEvent.compressor_id == compressor_id)
        .scalar() or 0
    )
    corrective = (
        db.query(func.count(ServiceEvent.id))
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_category == "corrective",
        )
        .scalar() or 0
    )
    preventive = (
        db.query(func.count(ServiceEvent.id))
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_category == "preventive_maintenance",
        )
        .scalar() or 0
    )
    last_date = (
        db.query(func.max(ServiceEvent.event_date))
        .filter(ServiceEvent.compressor_id == compressor_id)
        .scalar()
    )

    return CompressorDetail(
        id=comp.id,
        unit_id=comp.unit_id,
        raw_source_unit_ids=comp.raw_source_unit_ids,
        equipment_number=comp.equipment_number,
        compressor_type=comp.compressor_type,
        manufacturer=comp.manufacturer,
        model=comp.model,
        status=comp.status,
        current_run_hours=comp.current_run_hours,
        first_seen_date=comp.first_seen_date,
        site_id=comp.site_id,
        created_at=comp.created_at,
        site=comp.site,
        total_events=total,
        corrective_events=corrective,
        preventive_events=preventive,
        last_service_date=last_date,
    )


@router.get("/{compressor_id}/timeline", response_model=list[ServiceEventListItem])
def get_timeline(compressor_id: str, limit: int = 100, db: Session = Depends(get_db)):
    comp = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Compressor not found")

    return (
        db.query(ServiceEvent)
        .filter(ServiceEvent.compressor_id == compressor_id)
        .order_by(ServiceEvent.event_date.desc().nullslast())
        .limit(limit)
        .all()
    )


@router.get("/{compressor_id}/issues", response_model=list[CompressorIssueFrequency])
def get_issues(compressor_id: str, db: Session = Depends(get_db)):
    comp = db.query(Compressor).filter(Compressor.id == compressor_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Compressor not found")

    rows = (
        db.query(
            ServiceEvent.event_category,
            func.count(ServiceEvent.id).label("cnt"),
            func.max(ServiceEvent.event_date).label("last_date"),
            func.avg(ServiceEvent.run_hours_at_event).label("avg_hours"),
        )
        .filter(
            ServiceEvent.compressor_id == compressor_id,
            ServiceEvent.event_category.isnot(None),
        )
        .group_by(ServiceEvent.event_category)
        .order_by(func.count(ServiceEvent.id).desc())
        .all()
    )

    return [
        CompressorIssueFrequency(
            category=r[0],
            count=r[1],
            last_occurrence=r[2],
            avg_run_hours=round(r[3], 1) if r[3] else None,
        )
        for r in rows
    ]
