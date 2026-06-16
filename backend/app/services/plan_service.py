from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Plan, PlanItem, Platform, Quarter, Task, TaskPlatform, Zone
from app.read_models import TaskRanked
from app.schemas import PlanItemPlacement
from app.services.auto_placement import AutoPlacementService


class PlanService:
    def __init__(self, db: Session):
        self.db = db

    # --- кварталы ---
    def create_quarter(self, data, user_id: int | None) -> Quarter:
        quarter = Quarter(
            quarter_name=data.quarter_name,
            quarter_year=data.quarter_year,
            quarter_number=data.quarter_number,
            start_date=data.start_date,
            end_date=data.end_date,
            created_by_user_id=user_id,
        )
        self.db.add(quarter)
        self.db.commit()
        self.db.refresh(quarter)
        return quarter

    def list_quarters(self) -> list[Quarter]:
        stmt = select(Quarter).order_by(Quarter.quarter_year.desc(), Quarter.quarter_number.desc())
        return list(self.db.scalars(stmt).all())

    def rename_quarter(self, quarter_id: int, name: str) -> Quarter:
        q = self.db.get(Quarter, quarter_id)
        if q is None:
            raise ValueError("Метаспринт не найден")
        q.quarter_name = name
        self.db.commit()
        self.db.refresh(q)
        return q

    def delete_quarter(self, quarter_id: int) -> None:
        q = self.db.get(Quarter, quarter_id)
        if q is None:
            raise ValueError("Метаспринт не найден")
        for plan in self.db.scalars(select(Plan).where(Plan.quarter_id == quarter_id)).all():
            self.db.delete(plan)  # plan_items каскадятся
        self.db.delete(q)
        self.db.commit()

    # --- планы ---
    def rename_plan(self, plan_id: int, name: str) -> Plan:
        plan = self.db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("План не найден")
        plan.plan_name = name
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def next_plan_name(self, quarter_id: int) -> str:
        """Нумерация планов — своя в каждом метаспринте (сбрасывается)."""
        n = self.db.scalar(
            select(func.count(Plan.plan_id)).where(Plan.quarter_id == quarter_id)
        ) or 0
        return f"План {n + 1}"

    def create_plan(self, quarter_id: int, plan_name: str | None, user_id: int | None) -> Plan:
        """Пустой план (без задач). Имя — автонумерация в рамках метаспринта, если не задано."""
        name = plan_name or self.next_plan_name(quarter_id)
        plan = Plan(quarter_id=quarter_id, plan_name=name, created_by_user_id=user_id)
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def add_task(self, plan_id: int, task_id: int, user_id: int | None) -> None:
        self._require_draft(plan_id)
        exists = self.db.scalar(
            select(PlanItem).where(PlanItem.plan_id == plan_id, PlanItem.task_id == task_id)
        )
        if exists:
            return
        pos = self.db.scalar(
            select(func.count(PlanItem.plan_item_id)).where(PlanItem.plan_id == plan_id)
        ) or 0
        self.db.add(PlanItem(
            plan_id=plan_id, task_id=task_id, added_by_user_id=user_id, item_position=pos,
        ))
        self.db.commit()

    def remove_task(self, plan_id: int, task_id: int) -> None:
        self._require_draft(plan_id)
        item = self.db.scalar(
            select(PlanItem).where(PlanItem.plan_id == plan_id, PlanItem.task_id == task_id)
        )
        if item:
            self.db.delete(item)
            self.db.commit()

    def reorder(self, plan_id: int, task_ids: list[int]) -> None:
        self._require_draft(plan_id)
        items = {it.task_id: it for it in self.items(plan_id)}
        for pos, tid in enumerate(task_ids):
            it = items.get(tid)
            if it:
                it.item_position = pos
        self.db.commit()

    def plan_task_ids(self, plan_id: int) -> set[int]:
        return set(self.db.scalars(
            select(PlanItem.task_id).where(PlanItem.plan_id == plan_id)
        ).all())

    def plan_tasks(self, plan_id: int) -> list[TaskRanked]:
        """Задачи плана в ручном порядке (item_position)."""
        items = self.items(plan_id)  # уже order_by zone_id, item_position
        ordered = sorted(items, key=lambda it: it.item_position)
        if not ordered:
            return []
        ranked = {
            r.task_id: r for r in self.db.scalars(
                select(TaskRanked).where(TaskRanked.task_id.in_([it.task_id for it in ordered]))
            ).all()
        }
        return [ranked[it.task_id] for it in ordered if it.task_id in ranked]

    def save_presentation(self, plan_id: int, data: dict) -> None:
        self._require_draft(plan_id)
        plan = self.db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("План не найден")
        plan.presentation = data
        self.db.commit()

    def set_status(self, plan_id: int, value: str, user_id: int | None) -> Plan:
        if value not in ("draft", "approved", "archived"):
            raise ValueError("Неверный статус")
        plan = self.db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("План не найден")
        # Несколько утверждённых планов в метаспринте разрешены — прочие НЕ архивируем.
        if value == "approved":
            from datetime import datetime, timezone
            plan.approved_by_user_id = user_id
            plan.approved_at = datetime.now(timezone.utc)
        plan.plan_status = value
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def _require_draft(self, plan_id: int) -> None:
        plan = self.db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("План не найден")
        if plan.plan_status != "draft":
            raise PermissionError("План не в статусе «черновик» — редактирование запрещено")

    def list_plans(self, quarter_id: int | None = None) -> list[Plan]:
        stmt = select(Plan).order_by(Plan.created_at.desc())
        if quarter_id is not None:
            stmt = stmt.where(Plan.quarter_id == quarter_id)
        return list(self.db.scalars(stmt).all())

    def get_plan(self, plan_id: int) -> Plan | None:
        return self.db.get(Plan, plan_id)

    def delete_plan(self, plan_id: int) -> None:
        plan = self.db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("План не найден")
        self.db.delete(plan)  # PlanItem удалятся каскадом (ondelete CASCADE)
        self.db.commit()

    def approve_plan(self, plan_id: int, user_id: int | None) -> Plan:
        """Утвердить план = «загнать в метаспринт». Прочие планы метаспринта → archived."""
        from datetime import datetime, timezone

        plan = self.db.get(Plan, plan_id)
        if plan is None:
            raise ValueError("План не найден")
        # остальные approved-планы этого метаспринта уводим в архив
        siblings = self.db.scalars(
            select(Plan).where(
                Plan.quarter_id == plan.quarter_id,
                Plan.plan_id != plan_id,
                Plan.plan_status == "approved",
            )
        ).all()
        for s in siblings:
            s.plan_status = "archived"
        plan.plan_status = "approved"
        plan.approved_by_user_id = user_id
        plan.approved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def items(self, plan_id: int) -> list[PlanItem]:
        stmt = (
            select(PlanItem)
            .where(PlanItem.plan_id == plan_id)
            .order_by(PlanItem.zone_id, PlanItem.item_position)
        )
        return list(self.db.scalars(stmt).all())

    def zones(self) -> list[Zone]:
        return list(self.db.scalars(select(Zone).order_by(Zone.zone_id)).all())

    def platforms(self) -> list[Platform]:
        return list(self.db.scalars(select(Platform).order_by(Platform.platform_id)).all())

    def platform_estimates(self) -> dict[int, dict[int, float]]:
        """task_id -> {platform_id -> estimate_story_points} (только ненулевые)."""
        out: dict[int, dict[int, float]] = {}
        for tp in self.db.scalars(select(TaskPlatform)).all():
            if tp.estimate_story_points:
                out.setdefault(tp.task_id, {})[tp.platform_id] = float(
                    tp.estimate_story_points
                )
        return out

    def set_item_zone(self, plan_id: int, task_id: int, zone_id: int,
                      user_id: int | None) -> None:
        item = self.db.scalar(
            select(PlanItem).where(
                PlanItem.plan_id == plan_id, PlanItem.task_id == task_id
            )
        )
        if item is None:
            self.db.add(PlanItem(
                plan_id=plan_id, task_id=task_id, zone_id=zone_id,
                added_by_user_id=user_id,
            ))
        else:
            item.zone_id = zone_id
        self.db.commit()

    def save_placement(self, plan_id: int, placements: list[PlanItemPlacement],
                       user_id: int | None) -> int:
        """Переписывает раскладку плана: zone + позиция для каждой задачи (upsert)."""
        existing = {it.task_id: it for it in self.items(plan_id)}
        seen: set[int] = set()
        for pl in placements:
            seen.add(pl.task_id)
            item = existing.get(pl.task_id)
            if item is None:
                self.db.add(PlanItem(
                    plan_id=plan_id,
                    task_id=pl.task_id,
                    zone_id=pl.zone_id,
                    added_by_user_id=user_id,
                    item_position=pl.item_position,
                ))
            else:
                item.zone_id = pl.zone_id
                item.item_position = pl.item_position
        self.db.commit()
        return len(seen)
