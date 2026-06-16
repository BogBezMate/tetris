from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_editor
from app.models import User
from app.schemas import PlatformOut, TaskRankedOut, TaskUpdate
from app.services.jira_sync import JiraSyncService
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRankedOut])
def list_ranked(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return TaskService(db).list_ranked()


@router.get("/{task_id}/platforms", response_model=list[PlatformOut])
def task_platforms(task_id: int, db: Session = Depends(get_db),
                   _: User = Depends(get_current_user)):
    return [
        PlatformOut(
            platform_name=tp.platform.platform_name,
            is_required=tp.is_required,
            estimate_story_points=(
                float(tp.estimate_story_points)
                if tp.estimate_story_points is not None
                else None
            ),
        )
        for tp in TaskService(db).platforms_for(task_id)
    ]


@router.post("/reload-from-file")
def reload_from_file(db: Session = Depends(get_db), _: User = Depends(require_editor)):
    """Этап 5: перечитать response_example.json в базу (временно вместо вебхука)."""
    return JiraSyncService(db).load_from_file()


@router.patch("/{task_id}", response_model=TaskRankedOut)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db),
                _: User = Depends(require_editor)):
    svc = TaskService(db)
    try:
        svc.update_task(task_id, data)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    return svc.get_ranked(task_id)


@router.post("/{task_id}/sync-jira")
def sync_jira(task_id: int, db: Session = Depends(get_db),
              _: User = Depends(require_editor)):
    """Заглушка: ручная синхронизация задачи с Jira (реальная отправка — этап 12)."""
    try:
        return TaskService(db).sync_to_jira(task_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
