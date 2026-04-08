"""Manager directory — configuration and review-note name suggestions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event_models import ServiceEventNote
from app.models.master_models import Manager
from app.schemas.organization_schemas import ManagerListItem, NameCreate

router = APIRouter(prefix="/api/managers", tags=["managers"])


@router.get("/", response_model=list[ManagerListItem])
def list_managers(
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    rows = db.query(Manager).order_by(Manager.name).limit(limit).all()
    return [ManagerListItem.model_validate(m) for m in rows]


@router.post("/", response_model=ManagerListItem, status_code=201)
def create_manager(body: NameCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    existing = db.query(Manager).filter(func.lower(Manager.name) == func.lower(name)).first()
    if existing:
        raise HTTPException(status_code=409, detail="A manager with this name already exists")
    m = Manager(name=name)
    db.add(m)
    db.commit()
    db.refresh(m)
    return ManagerListItem.model_validate(m)


@router.delete("/{manager_id}", status_code=204)
def delete_manager(manager_id: str, db: Session = Depends(get_db)):
    m = db.query(Manager).filter(Manager.id == manager_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Manager not found")
    db.delete(m)
    db.commit()
    return None


@router.get("/suggestions", response_model=list[str])
def manager_name_suggestions(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Distinct review-comment author names not already in the manager directory."""
    known = {r[0].lower() for r in db.query(Manager.name).all() if r[0]}
    rows = (
        db.query(ServiceEventNote.author_name)
        .filter(
            ServiceEventNote.note_type == "review_comment",
            ServiceEventNote.author_name.isnot(None),
            ServiceEventNote.author_name != "",
        )
        .distinct()
        .order_by(ServiceEventNote.author_name)
        .limit(limit * 2)
        .all()
    )
    out: list[str] = []
    for (raw,) in rows:
        if not raw or not raw.strip():
            continue
        cleaned = raw.strip()
        if cleaned.lower() in known:
            continue
        out.append(cleaned)
        if len(out) >= limit:
            break
    return sorted(set(out), key=str.lower)
