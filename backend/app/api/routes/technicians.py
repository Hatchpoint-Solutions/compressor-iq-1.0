"""Technician directory for work order assignment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.master_models import Technician
from app.schemas.organization_schemas import NameCreate
from app.schemas.work_order_schemas import TechnicianListItem

router = APIRouter(prefix="/api/technicians", tags=["technicians"])


@router.get("/", response_model=list[TechnicianListItem])
def list_technicians(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Technician)
        .order_by(Technician.name)
        .limit(limit)
        .all()
    )
    return [TechnicianListItem.model_validate(t) for t in rows]


@router.post("/", response_model=TechnicianListItem, status_code=201)
def create_technician(body: NameCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    existing = db.query(Technician).filter(func.lower(Technician.name) == func.lower(name)).first()
    if existing:
        raise HTTPException(status_code=409, detail="A technician with this name already exists")
    t = Technician(name=name, event_count=0)
    db.add(t)
    db.commit()
    db.refresh(t)
    return TechnicianListItem.model_validate(t)


@router.delete("/{technician_id}", status_code=204)
def delete_technician(technician_id: str, db: Session = Depends(get_db)):
    t = db.query(Technician).filter(Technician.id == technician_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Technician not found")
    db.delete(t)
    db.commit()
    return None
