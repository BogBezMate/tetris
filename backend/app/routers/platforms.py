from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_editor
from app.models import Platform, User
from app.schemas import PlatformRef, PlatformVelocityIn

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformRef])
def list_platforms(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Platform).order_by(Platform.platform_id)).all()


@router.put("/velocity", response_model=list[PlatformRef])
def update_velocity(items: list[PlatformVelocityIn], db: Session = Depends(get_db),
                    _: User = Depends(require_editor)):
    """Редактирование velocity (SP в спринт на задачу) по платформам."""
    by_id = {p.platform_id: p for p in db.scalars(select(Platform)).all()}
    for item in items:
        p = by_id.get(item.platform_id)
        if p is not None:
            # минимум 0.01, чтобы формула спринтов не делила на ноль
            p.sp_per_sprint = max(0.01, float(item.sp_per_sprint))
    db.commit()
    return db.scalars(select(Platform).order_by(Platform.platform_id)).all()
