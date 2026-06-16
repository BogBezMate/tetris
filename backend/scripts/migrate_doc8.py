"""Доводка №8: добавить новые колонки без потери данных и пересоздать представление.

    python -m scripts.migrate_doc8

- platforms.sp_per_sprint (velocity, делитель «SP в спринт»; по умолчанию 5, у BPMSoft 6);
- tasks.max_sprints_override (ручной максимум спринтов; NULL/0 = авто);
- пересоздаёт v_tasks_ranked из app/sql/v_tasks_ranked.sql.

Идемпотентно (ADD COLUMN IF NOT EXISTS). Запуск из каталога backend/ при поднятом PostgreSQL.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.read_models import TaskRanked  # noqa: E402  (регистрирует маппинг вьюхи)

VIEW_SQL = (Path(__file__).resolve().parent.parent / "app" / "sql" / "v_tasks_ranked.sql")

ALTERS = [
    "ALTER TABLE platforms ADD COLUMN IF NOT EXISTS sp_per_sprint NUMERIC(6,2) NOT NULL DEFAULT 5",
    "UPDATE platforms SET sp_per_sprint = 6 WHERE platform_name = 'BPMSoft'",
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS max_sprints_override INTEGER",
]


def main() -> None:
    print("1) ALTER TABLE + velocity по умолчанию…")
    with engine.begin() as conn:
        for sql in ALTERS:
            conn.execute(text(sql))

    print("2) Пересоздаю представление v_tasks_ranked…")
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL.read_text(encoding="utf-8")))

    print("3) Контроль velocity:")
    with engine.begin() as conn:
        for name, sp in conn.execute(text(
            "SELECT platform_name, sp_per_sprint FROM platforms ORDER BY platform_name"
        )):
            print(f"   {name}: {sp}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
