"""AutoPlacementService — стартовая раскладка задач по колодцам.

Правила (как в n8n): колодец определяется по меткам задачи; если метка явно не
указывает колодец — задача попадает в «To be allocated», дальше редактор двигает руками.
Метки в Jira пишут по-разному (MetaSprint5, Metasprint), поэтому сопоставляем по
нормализованному началу строки.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Task, Zone

DEFAULT_ZONE = "To be allocated"

# Префикс нормализованной метки -> имя колодца.
_LABEL_PREFIX_TO_ZONE = {
    "metasprint": "MetaSprint",
    "meta": "MetaSprint",
    "alphasprint": "AlphaSprint",
    "alpha": "AlphaSprint",
    "opensprint": "OpenSprint",
    "open": "OpenSprint",
}


def _zone_for_labels(labels: list[str]) -> str:
    for label in labels:
        norm = "".join(ch for ch in label.lower() if ch.isalnum())
        for prefix, zone in _LABEL_PREFIX_TO_ZONE.items():
            if norm.startswith(prefix):
                return zone
    return DEFAULT_ZONE


def zone_for(labels: list[str], has_active_sprint: bool = False) -> str:
    """Колодец задачи. Приоритет: метка MetaSprint/AlphaSprint; если метки нет, но есть
    активный спринт (state=ACTIVE) → OpenSprint; иначе To be allocated.
    (Если у задачи есть и метка meta/alpha, и активный спринт — берём метку.)"""
    zone = _zone_for_labels(labels)
    if zone != DEFAULT_ZONE:
        return zone
    if has_active_sprint:
        return "OpenSprint"
    return DEFAULT_ZONE


class AutoPlacementService:
    def __init__(self, db: Session):
        self.db = db
        self._zones = {z.zone_name: z.zone_id for z in db.scalars(select(Zone)).all()}

    def zone_id_for(self, task: Task) -> int:
        zone_name = zone_for(
            [lbl.label_name for lbl in task.labels],
            getattr(task, "has_active_sprint", False),
        )
        return self._zones.get(zone_name) or self._zones[DEFAULT_ZONE]

    def place(self, tasks: list[Task]) -> dict[int, int]:
        """task_id -> zone_id для стартовой раскладки."""
        return {t.task_id: self.zone_id_for(t) for t in tasks}
