from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_editor
from app.models import GoalType, User
from app.read_models import TaskRanked
from app.schemas import (
    AddTaskIn,
    AutoOut,
    AutoRow,
    BoardColumn,
    BoardOut,
    GoalTypeOut,
    GridOut,
    GridRow,
    PlanCreate,
    PlanItemOut,
    PlanOut,
    PlatformRef,
    PresentationIn,
    QuarterCreate,
    QuarterOut,
    ReorderIn,
    SavePlacementRequest,
    TaskRankedOut,
    ZoneOut,
)
from app.services.auto_placement import _zone_for_labels
from app.services.plan_service import PlanService
from app.services.task_service import TaskService

router = APIRouter(prefix="/api", tags=["planning"])


@router.get("/zones", response_model=list[ZoneOut])
def zones(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return PlanService(db).zones()


@router.get("/goal-types", response_model=list[GoalTypeOut])
def goal_types(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from sqlalchemy import select
    return list(db.scalars(select(GoalType).order_by(GoalType.goal_type_id)).all())


@router.get("/quarters", response_model=list[QuarterOut])
def list_quarters(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return PlanService(db).list_quarters()


@router.post("/quarters", response_model=QuarterOut)
def create_quarter(data: QuarterCreate, db: Session = Depends(get_db),
                   user: User = Depends(require_editor)):
    return PlanService(db).create_quarter(data, user.user_id)


@router.put("/quarters/{quarter_id}/rename", response_model=QuarterOut)
def rename_quarter(quarter_id: int, name: str, db: Session = Depends(get_db),
                   _: User = Depends(require_editor)):
    try:
        return PlanService(db).rename_quarter(quarter_id, name)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.delete("/quarters/{quarter_id}")
def delete_quarter(quarter_id: int, db: Session = Depends(get_db),
                   _: User = Depends(require_editor)):
    try:
        PlanService(db).delete_quarter(quarter_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"ok": True}


@router.get("/plans", response_model=list[PlanOut])
def list_plans(quarter_id: int | None = None, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    return PlanService(db).list_plans(quarter_id)


@router.post("/plans", response_model=PlanOut)
def create_plan(data: PlanCreate, db: Session = Depends(get_db),
                user: User = Depends(require_editor)):
    return PlanService(db).create_plan(data.quarter_id, data.plan_name, user.user_id)


@router.put("/plans/{plan_id}/rename", response_model=PlanOut)
def rename_plan(plan_id: int, name: str, db: Session = Depends(get_db),
                _: User = Depends(require_editor)):
    try:
        return PlanService(db).rename_plan(plan_id, name)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get("/plans/{plan_id}/board", response_model=BoardOut)
def plan_board(plan_id: int, db: Session = Depends(get_db),
               _: User = Depends(get_current_user)):
    svc = PlanService(db)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")

    ranked = {r.task_id: r for r in db.query(TaskRanked).all()}
    items = svc.items(plan_id)
    by_zone: dict[int, list[PlanItemOut]] = {}
    for it in items:
        r = ranked.get(it.task_id)
        out = PlanItemOut(
            plan_item_id=it.plan_item_id,
            task_id=it.task_id,
            zone_id=it.zone_id,
            item_position=it.item_position,
            task=TaskRankedOut.model_validate(r) if r else None,
        )
        by_zone.setdefault(it.zone_id, []).append(out)

    columns = [
        BoardColumn(
            zone_id=z.zone_id,
            zone_name=z.zone_name,
            items=sorted(by_zone.get(z.zone_id, []), key=lambda i: i.item_position),
        )
        for z in svc.zones()
    ]
    return BoardOut(plan=PlanOut.model_validate(plan), columns=columns)


@router.put("/plans/{plan_id}/placement")
def save_placement(plan_id: int, data: SavePlacementRequest, db: Session = Depends(get_db),
                   user: User = Depends(require_editor)):
    svc = PlanService(db)
    if not svc.get_plan(plan_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")
    saved = svc.save_placement(plan_id, data.items, user.user_id)
    return {"saved": saved}


@router.put("/plans/{plan_id}/items/{task_id}/zone")
def set_item_zone(plan_id: int, task_id: int, zone_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_editor)):
    svc = PlanService(db)
    if not svc.get_plan(plan_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")
    svc.set_item_zone(plan_id, task_id, zone_id, user.user_id)
    return {"ok": True}


@router.post("/plans/{plan_id}/approve", response_model=PlanOut)
def approve_plan(plan_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_editor)):
    """Утвердить план = загнать в метаспринт (draft→approved)."""
    try:
        return PlanService(db).approve_plan(plan_id, user.user_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db),
                _: User = Depends(require_editor)):
    try:
        PlanService(db).delete_plan(plan_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"ok": True}


@router.get("/plans/{plan_id}/grid", response_model=GridOut)
def plan_grid(plan_id: int, db: Session = Depends(get_db),
              _: User = Depends(get_current_user)):
    """Плоская таблица плана: ТОЛЬКО задачи этого плана + Excel-слой (presentation)."""
    svc = PlanService(db)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")

    estimates = svc.platform_estimates()
    rows = [
        GridRow(
            task=TaskRankedOut.model_validate(r),
            platform_estimates=estimates.get(r.task_id, {}),
        )
        for r in svc.plan_tasks(plan_id)
    ]
    return GridOut(
        plan=PlanOut.model_validate(plan),
        platforms=[PlatformRef.model_validate(p) for p in svc.platforms()],
        zones=[ZoneOut.model_validate(z) for z in svc.zones()],
        rows=rows,
        presentation=plan.presentation,
    )


@router.post("/plans/{plan_id}/items")
def add_plan_item(plan_id: int, data: AddTaskIn, db: Session = Depends(get_db),
                  user: User = Depends(require_editor)):
    svc = PlanService(db)
    if not svc.get_plan(plan_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")
    try:
        svc.add_task(plan_id, data.task_id, user.user_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return {"ok": True}


@router.delete("/plans/{plan_id}/items/{task_id}")
def remove_plan_item(plan_id: int, task_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_editor)):
    svc = PlanService(db)
    if not svc.get_plan(plan_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")
    try:
        svc.remove_task(plan_id, task_id)
    except PermissionError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return {"ok": True}


@router.put("/plans/{plan_id}/reorder")
def reorder_plan(plan_id: int, data: ReorderIn, db: Session = Depends(get_db),
                 _: User = Depends(require_editor)):
    svc = PlanService(db)
    if not svc.get_plan(plan_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "План не найден")
    try:
        svc.reorder(plan_id, data.task_ids)
    except PermissionError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return {"ok": True}


@router.put("/plans/{plan_id}/status", response_model=PlanOut)
def set_plan_status(plan_id: int, value: str, db: Session = Depends(get_db),
                    user: User = Depends(require_editor)):
    try:
        return PlanService(db).set_status(plan_id, value, user.user_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.put("/plans/{plan_id}/presentation")
def save_presentation(plan_id: int, data: PresentationIn, db: Session = Depends(get_db),
                      user: User = Depends(require_editor)):
    try:
        PlanService(db).save_presentation(plan_id, data.data)
    except PermissionError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return {"ok": True}


@router.get("/autovygruzka", response_model=AutoOut)
def autovygruzka(plan_id: int | None = None, db: Session = Depends(get_db),
                 _: User = Depends(get_current_user)):
    """Все задачи + вычисленный колодец (по меткам). Фронт группирует по колодцам.

    plan_id (опц.) — пометить, какие задачи уже в этом плане (in_plan).
    """
    svc = PlanService(db)
    in_plan = svc.plan_task_ids(plan_id) if plan_id else set()
    estimates = svc.platform_estimates()
    rows = [
        AutoRow(
            task=TaskRankedOut.model_validate(r),
            zone_name=_zone_for_labels((r.labels or "").split(", ") if r.labels else []),
            in_plan=r.task_id in in_plan,
            platform_estimates=estimates.get(r.task_id, {}),
        )
        for r in TaskService(db).list_ranked()
    ]
    return AutoOut(
        platforms=[PlatformRef.model_validate(p) for p in svc.platforms()],
        rows=rows,
    )
