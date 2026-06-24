from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Plan,
    PlanItem,
    PlanTaskEstimate,
    Platform,
    Quarter,
    QuarterVelocity,
    Task,
    TaskPlatform,
    Zone,
)
from app.read_models import TaskRanked
from app.schemas import GridRow, PlanItemPlacement, PlatformRef, TaskRankedOut
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

    def duplicate_plan(self, src_plan_id: int, user_id: int | None) -> Plan:
        """Создать новый план на основе существующего: копирует задачи, раскладку
        (presentation) и остаточные оценки. Новый план — черновик."""
        src = self.db.get(Plan, src_plan_id)
        if src is None:
            raise ValueError("План не найден")
        new = Plan(
            quarter_id=src.quarter_id,
            plan_name=f"{src.plan_name} (копия)",
            created_by_user_id=user_id,
            plan_status="draft",
            presentation=src.presentation,  # JSON-слой (раскладка/заливки/заметки/порядок)
        )
        self.db.add(new)
        self.db.flush()  # нужен new.plan_id
        # задачи плана (зоны/позиции)
        for it in self.items(src_plan_id):
            self.db.add(PlanItem(
                plan_id=new.plan_id, task_id=it.task_id, zone_id=it.zone_id,
                added_by_user_id=user_id, item_position=it.item_position,
            ))
        # остаточные оценки в плане
        for pe in self.db.scalars(
            select(PlanTaskEstimate).where(PlanTaskEstimate.plan_id == src_plan_id)
        ).all():
            self.db.add(PlanTaskEstimate(
                plan_id=new.plan_id, task_id=pe.task_id,
                platform_id=pe.platform_id, estimate_sp=pe.estimate_sp,
            ))
        self.db.commit()
        self.db.refresh(new)
        return new

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
        # Историчность: утверждение И архив — заморожены (снимок данных).
        # - approved: всегда делаем свежий снимок;
        # - archived: если снимка ещё нет (архив напрямую из черновика) — делаем; иначе сохраняем
        #   снимок от момента утверждения;
        # - draft: сбрасываем снимок (план снова живой и редактируемый).
        if value == "approved":
            self.freeze_snapshot(plan)
        elif value == "archived":
            if not plan.approved_snapshot:
                self.freeze_snapshot(plan)
        elif value == "draft":
            plan.approved_snapshot = None
        self.db.commit()
        self.db.refresh(plan)
        return plan

    # --- построение таблицы плана (live) и снимок при утверждении ---
    def compute_grid(self, plan) -> tuple[list, list, dict]:
        """Строки/платформы/velocity для таблицы плана из ЖИВЫХ данных.
        Используется и grid-эндпоинтом, и снимком при утверждении (чтобы не расходились)."""
        import math

        estimates = self.platform_estimates()
        overrides = self.plan_estimate_overrides(plan.plan_id)
        sps = self.quarter_sp_per_sprint(plan.quarter_id)  # делитель SP/спринт метаспринта
        rows = []
        for r in self.plan_tasks(plan.plan_id):
            base = dict(estimates.get(r.task_id, {}))
            ov = overrides.get(r.task_id, {})
            merged = {**base, **ov}  # остаток плана переопределяет оценку Jira
            task = TaskRankedOut.model_validate(r)
            if r.max_sprints_override and r.max_sprints_override > 0:
                task.max_sprints = float(r.max_sprints_override)
            else:
                sc = [est / sps[pid] for pid, est in merged.items() if est and sps.get(pid)]
                task.max_sprints = float(math.ceil(max(sc))) if sc else 0.0
            rows.append(GridRow(
                task=task, platform_estimates=merged, overridden_platforms=list(ov.keys()),
            ))
        platforms_out = []
        for p in self.platforms():
            pr = PlatformRef.model_validate(p)
            pr.sp_per_sprint = sps.get(p.platform_id, pr.sp_per_sprint)
            platforms_out.append(pr)
        return rows, platforms_out, self.quarter_velocity_map(plan.quarter_id)

    def freeze_snapshot(self, plan) -> None:
        """Снимок таблицы плана на момент утверждения (историчность)."""
        rows, platforms_out, velocity = self.compute_grid(plan)
        plan.approved_snapshot = {
            "rows": [r.model_dump(mode="json") for r in rows],
            "platforms": [p.model_dump(mode="json") for p in platforms_out],
            "velocity_per_meta": {str(k): v for k, v in velocity.items()},
        }

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
            s.plan_status = "archived"  # снимок у них остаётся от их утверждения
        plan.plan_status = "approved"
        plan.approved_by_user_id = user_id
        plan.approved_at = datetime.now(timezone.utc)
        self.freeze_snapshot(plan)  # историчность: фиксируем данные плана
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

    # --- Velocity платформ в метаспринте (ёмкость + делитель SP/спринт) ---
    def quarter_velocities(self, quarter_id: int) -> list[dict]:
        """Все платформы + ёмкость и делитель SP/спринт в этом метаспринте (нет записи → None)."""
        rows = {
            qv.platform_id: qv
            for qv in self.db.scalars(
                select(QuarterVelocity).where(QuarterVelocity.quarter_id == quarter_id)
            ).all()
        }
        out: list[dict] = []
        for p in self.platforms():
            qv = rows.get(p.platform_id)
            out.append({
                "platform_id": p.platform_id,
                "platform_name": p.platform_name,
                "capacity_sp": float(qv.capacity_sp) if qv and qv.capacity_sp is not None else None,
                "sp_per_sprint": float(qv.sp_per_sprint) if qv and qv.sp_per_sprint is not None else None,
                "sp_per_sprint_default": float(p.sp_per_sprint or 5),
            })
        return out

    def quarter_velocity_map(self, quarter_id: int) -> dict[int, float]:
        """platform_id -> ёмкость за метаспринт (только заданные)."""
        out: dict[int, float] = {}
        for qv in self.db.scalars(
            select(QuarterVelocity).where(QuarterVelocity.quarter_id == quarter_id)
        ).all():
            if qv.capacity_sp is not None:
                out[qv.platform_id] = float(qv.capacity_sp)
        return out

    def quarter_sp_per_sprint(self, quarter_id: int) -> dict[int, float]:
        """platform_id -> эффективный делитель: override метаспринта, иначе глобальный дефолт."""
        overrides = {
            qv.platform_id: float(qv.sp_per_sprint)
            for qv in self.db.scalars(
                select(QuarterVelocity).where(QuarterVelocity.quarter_id == quarter_id)
            ).all()
            if qv.sp_per_sprint is not None
        }
        out: dict[int, float] = {}
        for p in self.platforms():
            out[p.platform_id] = overrides.get(p.platform_id) or float(p.sp_per_sprint or 5)
        return out

    def save_quarter_velocities(self, quarter_id: int, items) -> None:
        """Upsert ёмкости и делителя по платформам метаспринта.

        В каждом поле None/<=0 = снять (вернуть к дефолту). Запись удаляется,
        когда оба поля сняты.
        """
        if self.db.get(Quarter, quarter_id) is None:
            raise ValueError("Метаспринт не найден")
        existing = {
            qv.platform_id: qv
            for qv in self.db.scalars(
                select(QuarterVelocity).where(QuarterVelocity.quarter_id == quarter_id)
            ).all()
        }
        for item in items:
            cap = item.capacity_sp if (item.capacity_sp and item.capacity_sp > 0) else None
            sps = item.sp_per_sprint if (item.sp_per_sprint and item.sp_per_sprint > 0) else None
            qv = existing.get(item.platform_id)
            if cap is None and sps is None:
                if qv is not None:
                    self.db.delete(qv)
                continue
            if qv is None:
                self.db.add(QuarterVelocity(
                    quarter_id=quarter_id, platform_id=item.platform_id,
                    capacity_sp=cap, sp_per_sprint=sps,
                ))
            else:
                qv.capacity_sp = cap
                qv.sp_per_sprint = sps
        self.db.commit()

    # --- Остаточные оценки задачи в рамках плана ---
    def plan_estimate_overrides(self, plan_id: int) -> dict[int, dict[int, float]]:
        """task_id -> {platform_id -> остаточная оценка в этом плане}."""
        out: dict[int, dict[int, float]] = {}
        for pe in self.db.scalars(
            select(PlanTaskEstimate).where(PlanTaskEstimate.plan_id == plan_id)
        ).all():
            if pe.estimate_sp is not None:
                out.setdefault(pe.task_id, {})[pe.platform_id] = float(pe.estimate_sp)
        return out

    def save_plan_estimates(self, plan_id: int, task_id: int, items) -> None:
        """Upsert остаточных оценок задачи в плане. estimate_sp None → сброс к Jira (удалить)."""
        self._require_draft(plan_id)
        existing = {
            pe.platform_id: pe
            for pe in self.db.scalars(
                select(PlanTaskEstimate).where(
                    PlanTaskEstimate.plan_id == plan_id,
                    PlanTaskEstimate.task_id == task_id,
                )
            ).all()
        }
        for item in items:
            pe = existing.get(item.platform_id)
            if item.estimate_sp is None:
                if pe is not None:
                    self.db.delete(pe)
                continue
            if pe is None:
                self.db.add(PlanTaskEstimate(
                    plan_id=plan_id, task_id=task_id,
                    platform_id=item.platform_id, estimate_sp=item.estimate_sp,
                ))
            else:
                pe.estimate_sp = item.estimate_sp
        self.db.commit()

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
