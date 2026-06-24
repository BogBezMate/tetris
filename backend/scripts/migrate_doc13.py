"""Доводка №13: делитель «SP за спринт» индивидуально для метаспринта.

    python -m scripts.migrate_doc13

Добавляет колонку quarter_velocities.sp_per_sprint (NULL = глобальный дефолт).
Идемпотентно (ADD COLUMN IF NOT EXISTS). Запуск из каталога backend/ при поднятом PostgreSQL.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

DDL = [
    "ALTER TABLE quarter_velocities ADD COLUMN IF NOT EXISTS sp_per_sprint NUMERIC(6,2)",
]


def main() -> None:
    print("1) ALTER quarter_velocities ADD sp_per_sprint…")
    with engine.begin() as conn:
        for sql in DDL:
            conn.execute(text(sql))

    print("2) Контроль (колонка существует):")
    with engine.begin() as conn:
        col = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='quarter_velocities' AND column_name='sp_per_sprint'"
        )).scalar()
        print(f"   quarter_velocities.sp_per_sprint: {'OK' if col else 'НЕТ'}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
