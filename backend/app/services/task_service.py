from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import JiraSyncLog, Task, TaskPlatform
from app.read_models import TaskRanked


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def list_ranked(self) -> list[TaskRanked]:
        """Ранжированный список: по EBITDA на стори-поинт, по убыванию."""
        stmt = select(TaskRanked).order_by(
            TaskRanked.ebitda_per_story_point.desc(),
            TaskRanked.jira_key,
        )
        return list(self.db.scalars(stmt).all())

    def get_ranked(self, task_id: int) -> TaskRanked | None:
        return self.db.get(TaskRanked, task_id)

    def platforms_for(self, task_id: int) -> list[TaskPlatform]:
        stmt = (
            select(TaskPlatform)
            .where(TaskPlatform.task_id == task_id)
            .order_by(TaskPlatform.is_required.desc())
        )
        return list(self.db.scalars(stmt).all())

    def count(self) -> int:
        return self.db.scalar(select(func.count(Task.task_id))) or 0

    def update_task(self, task_id: int, data) -> Task:
        """Редактирование задачи в нашей БД (поля + оценки платформ)."""
        task = self.db.get(Task, task_id)
        if task is None:
            raise ValueError("Задача не найдена")

        simple = data.model_dump(exclude_unset=True, exclude={"platform_estimates"})
        for field, value in simple.items():
            setattr(task, field, value)

        if data.platform_estimates is not None:
            by_platform = {tp.platform_id: tp for tp in task.platforms}
            for pe in data.platform_estimates:
                tp = by_platform.get(pe.platform_id)
                if tp is None:
                    tp = TaskPlatform(platform_id=pe.platform_id, is_required=False)
                    task.platforms.append(tp)
                if pe.estimate_story_points is not None:
                    tp.estimate_story_points = pe.estimate_story_points
                if pe.is_required is not None:
                    tp.is_required = pe.is_required

        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def sync_to_jira(self, task_id: int) -> dict:
        """Заглушка записи в Jira: логируем намерение. Реальная отправка — этап 12."""
        task = self.db.get(Task, task_id)
        if task is None:
            raise ValueError("Задача не найдена")
        self.db.add(JiraSyncLog(
            task_id=task.task_id,
            sync_direction="out",
            sync_payload={"jira_key": task.jira_key, "note": "ручная синхронизация (заглушка)"},
            sync_status="ok",
            sync_error_message="Заглушка: реальная запись в Jira включится на этапе 12 (вебхук/доступ от куратора)",
        ))
        self.db.commit()
        return {"ok": True, "stub": True, "jira_key": task.jira_key}
