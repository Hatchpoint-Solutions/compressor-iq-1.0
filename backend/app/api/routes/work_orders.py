"""Work order CRUD — manager dispatch and technician execution."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import verify_api_key_if_configured
from app.schemas.work_order_schemas import (
    WorkOrderCreate,
    WorkOrderDetail,
    WorkOrderListItem,
    WorkOrderStepResponse,
    WorkOrderStepUpdate,
    WorkOrderUpdate,
)
from app.services import work_order_service as wo_svc
from app.services.work_order_service import get_work_order

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


def _to_list_item(wo) -> WorkOrderListItem:
    unit_id = wo.compressor.unit_id if wo.compressor else ""
    tech_name = wo.assigned_technician.name if wo.assigned_technician else None
    return WorkOrderListItem(
        id=wo.id,
        title=wo.title,
        description=wo.description,
        compressor_id=wo.compressor_id,
        unit_id=unit_id,
        source=wo.source,
        status=wo.status,
        assigned_technician_id=wo.assigned_technician_id,
        assigned_technician_name=tech_name,
        recommendation_id=wo.recommendation_id,
        created_at=wo.created_at,
        updated_at=wo.updated_at,
        completed_at=wo.completed_at,
    )


def _to_detail(wo) -> WorkOrderDetail:
    base = _to_list_item(wo).model_dump()
    steps = [
        WorkOrderStepResponse.model_validate(s) for s in sorted(wo.steps, key=lambda x: x.step_number)
    ]
    return WorkOrderDetail(**base, steps=steps)


@router.get("/", response_model=list[WorkOrderListItem])
def list_work_orders(
    status: str | None = Query(None),
    compressor_id: str | None = Query(None),
    assigned_technician_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows = wo_svc.list_work_orders(
        db,
        status=status,
        compressor_id=compressor_id,
        assigned_technician_id=assigned_technician_id,
        limit=limit,
    )
    return [_to_list_item(wo) for wo in rows]


@router.post(
    "/",
    response_model=WorkOrderDetail,
    dependencies=[Depends(verify_api_key_if_configured)],
)
def create_work_order(body: WorkOrderCreate, db: Session = Depends(get_db)):
    try:
        wo = wo_svc.create_work_order(
            db,
            compressor_id=body.compressor_id,
            title=body.title,
            source=body.source,
            description=body.description,
            recommendation_id=body.recommendation_id,
            issue_category=body.issue_category,
            assigned_technician_id=body.assigned_technician_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    full = get_work_order(db, wo.id)
    assert full is not None
    return _to_detail(full)


@router.get("/{work_order_id}", response_model=WorkOrderDetail)
def get_one(work_order_id: str, db: Session = Depends(get_db)):
    wo = get_work_order(db, work_order_id)
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    return _to_detail(wo)


@router.patch(
    "/{work_order_id}",
    response_model=WorkOrderDetail,
    dependencies=[Depends(verify_api_key_if_configured)],
)
def patch_work_order(
    work_order_id: str,
    body: WorkOrderUpdate,
    db: Session = Depends(get_db),
):
    try:
        wo = wo_svc.update_work_order(
            db,
            work_order_id,
            status=body.status,
            assigned_technician_id=body.assigned_technician_id,
            title=body.title,
            description=body.description,
            unset_assignee=body.clear_assigned_technician,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")
    full = get_work_order(db, work_order_id)
    assert full is not None
    return _to_detail(full)


@router.patch(
    "/{work_order_id}/steps/{step_id}",
    response_model=WorkOrderStepResponse,
    dependencies=[Depends(verify_api_key_if_configured)],
)
def patch_step(
    work_order_id: str,
    step_id: str,
    body: WorkOrderStepUpdate,
    db: Session = Depends(get_db),
):
    step = wo_svc.update_work_order_step(
        db,
        work_order_id,
        step_id,
        is_completed=body.is_completed,
        notes=body.notes,
    )
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    return WorkOrderStepResponse.model_validate(step)
