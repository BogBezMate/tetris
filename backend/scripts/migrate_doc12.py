"""Доводка №12: новые таблицы для velocity per meta и остаточных оценок в плане.

    python -m scripts.migrate_doc12

- quarter_velocities — ёмкость платформы за метаспринт (Velocity per Meta);
- plan_task_estimates — остаточная оценка задачи по платформе в рамках плана.

Идемпотентно (CREATE TABLE IF NOT EXISTS). Запуск из каталога backend/ при поднятом PostgreSQL.
Представление v_tasks_ranked не меняется (метрики те же), пересоздавать не нужно.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

DDL = [
    """
    CREATE TABLE IF NOT EXISTS quarter_velocities (
        quarter_velocity_id SERIAL PRIMARY KEY,
        quarter_id  INTEGER NOT NULL REFERENCES quarters(quarter_id) ON DELETE CASCADE,
        platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
        capacity_sp NUMERIC(10,2),
        CONSTRAINT uq_quarter_platform_velocity UNIQUE (quarter_id, platform_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plan_task_estimates (
        plan_task_estimate_id SERIAL PRIMARY KEY,
        plan_id     INTEGER NOT NULL REFERENCES plans(plan_id) ON DELETE CASCADE,
        task_id     INTEGER NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
        platform_id INTEGER NOT NULL REFERENCES platforms(platform_id),
        estimate_sp NUMERIC(10,2),
        CONSTRAINT uq_plan_task_platform UNIQUE (plan_id, task_id, platform_id)
    )
    """,
]


def main() -> None:
    print("1) Создаю таблицы quarter_velocities, plan_task_estimates…")
    with engine.begin() as conn:
        for sql in DDL:
            conn.execute(text(sql))

    print("2) Контроль (таблицы существуют):")
    with engine.begin() as conn:
        for tbl in ("quarter_velocities", "plan_task_estimates"):
            exists = conn.execute(text(
                "SELECT to_regclass(:t)"
            ), {"t": tbl}).scalar()
            print(f"   {tbl}: {'OK' if exists else 'НЕТ'}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
