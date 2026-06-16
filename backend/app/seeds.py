"""Наполнение справочников: 17 платформ, типы целей, 4 колодца.

Идемпотентно: повторный запуск ничего не дублирует. Источник имён и id полей —
app.jira_fields (единый источник правды).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import jira_fields as jf
from app.models import GoalType, Platform, Zone


def seed_goal_types(db: Session) -> None:
    for name, affects in jf.GOAL_TYPES.items():
        existing = db.scalar(select(GoalType).where(GoalType.goal_type_name == name))
        if existing:
            existing.affects_effect = affects
        else:
            db.add(GoalType(goal_type_name=name, affects_effect=affects))


def seed_platforms(db: Session) -> None:
    for name, field_id in jf.PLATFORM_FIELDS.items():
        existing = db.scalar(select(Platform).where(Platform.platform_name == name))
        if existing:
            existing.jira_field_id = field_id
        else:
            db.add(Platform(platform_name=name, jira_field_id=field_id))


def seed_zones(db: Session) -> None:
    for name in jf.ZONES:
        existing = db.scalar(select(Zone).where(Zone.zone_name == name))
        if not existing:
            db.add(Zone(zone_name=name))


def seed_all(db: Session) -> None:
    seed_goal_types(db)
    seed_platforms(db)
    seed_zones(db)
    db.commit()


if __name__ == "__main__":
    from app.database import SessionLocal

    with SessionLocal() as session:
        seed_all(session)
        print("Справочники заполнены: "
              f"{len(jf.GOAL_TYPES)} типов целей, "
              f"{len(jf.PLATFORM_FIELDS)} платформ, "
              f"{len(jf.ZONES)} колодца.")
