"""Загрузка задач из распарсенной структуры в базу (upsert по jira_internal_id).

Используется и файловой загрузкой (этап 5), и живым вебхуком (этап 12) — точка входа
одна и та же, меняется только источник payload.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jira_mapper import JiraFieldMapper, ParsedTask, load_issues
from app.models import GoalType, JiraSyncLog, Platform, Task, TaskLabel, TaskPlatform


def _resolve_goal_type_id(db: Session, name: str | None) -> int | None:
    if not name:
        return None
    gt = db.scalar(select(GoalType).where(GoalType.goal_type_name == name))
    return gt.goal_type_id if gt else None


def _platform_ids(db: Session) -> dict[str, int]:
    return {p.platform_name: p.platform_id for p in db.scalars(select(Platform)).all()}


def upsert_parsed_task(db: Session, parsed: ParsedTask, platform_ids: dict[str, int]) -> Task:
    task = db.scalar(select(Task).where(Task.jira_internal_id == parsed.jira_internal_id))
    if task is None:
        task = Task(jira_internal_id=parsed.jira_internal_id)
        db.add(task)

    task.jira_key = parsed.jira_key
    task.goal_type_id = _resolve_goal_type_id(db, parsed.goal_type_name)
    task.task_summary = parsed.task_summary
    task.issue_type = parsed.issue_type
    task.task_status = parsed.task_status
    task.business_unit = parsed.business_unit
    task.change_scope = parsed.change_scope
    task.customer_name = parsed.customer_name
    task.it_business_partner = parsed.it_business_partner
    task.ceo_priority = parsed.ceo_priority
    task.dod_text = parsed.dod_text
    task.company_effect_rub = parsed.company_effect_rub
    task.eta_months = parsed.eta_months
    task.adjusted_ebitda = parsed.adjusted_ebitda
    task.total_story_points = parsed.total_story_points
    task.contractor_cost_rub = parsed.contractor_cost_rub
    task.coefficient = parsed.coefficient
    task.current_sprint = parsed.current_sprint
    task.end_date = parsed.end_date
    task.baseline_end_date = parsed.baseline_end_date
    task.jira_updated_at = parsed.jira_updated_at
    task.synced_at = datetime.now(timezone.utc)

    # Сначала удаляем старые платформы/метки и сбрасываем в БД, потом вставляем новые —
    # иначе при upsert Postgres проверит uq_task_label/uq_task_platform до удаления старых
    # и упадёт с UniqueViolation.
    task.platforms.clear()
    task.labels.clear()
    db.flush()

    for p in parsed.platforms:
        pid = platform_ids.get(p.platform_name)
        if pid is None:
            continue
        task.platforms.append(
            TaskPlatform(
                platform_id=pid,
                is_required=p.is_required,
                estimate_story_points=p.estimate_story_points,
            )
        )

    for name in dict.fromkeys(parsed.labels):
        task.labels.append(TaskLabel(label_name=name))

    return task


def load_payload(db: Session, payload) -> dict:
    """Разбирает payload (issues[] / одна issue / вебхук) и грузит в базу."""
    mapper = JiraFieldMapper()
    platform_ids = _platform_ids(db)
    issues = load_issues(payload)
    loaded, failed = 0, 0

    for issue in issues:
        try:
            parsed = mapper.to_task(issue)
            task = upsert_parsed_task(db, parsed, platform_ids)
            db.flush()
            db.add(JiraSyncLog(
                task_id=task.task_id,
                sync_direction="in",
                sync_payload=issue,
                sync_status="ok",
            ))
            loaded += 1
        except Exception as exc:  # noqa: BLE001 — лог и продолжаем остальные задачи
            db.add(JiraSyncLog(
                sync_direction="in",
                sync_payload=issue if isinstance(issue, dict) else None,
                sync_status="error",
                sync_error_message=str(exc),
            ))
            failed += 1

    db.commit()
    return {"loaded": loaded, "failed": failed, "total": len(issues)}
