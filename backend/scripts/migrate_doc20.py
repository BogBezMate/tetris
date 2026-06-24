"""Доводка №20: OpenSprint по active-спринту + новые платформы.

    python -m scripts.migrate_doc20

- tasks.has_active_sprint (есть спринт state=ACTIVE → OpenSprint);
- пересоздаёт v_tasks_ranked (добавлено has_active_sprint);
- сидит новые платформы (PowerBI, Сервис Самопланирования) — seed_platforms идемпотентен.

Идемпотентно. Запуск из каталога backend/ при поднятом PostgreSQL. После — перезалить задачи.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine, SessionLocal  # noqa: E402
from app.read_models import TaskRanked  # noqa: E402,F401
from app.seeds import seed_platforms  # noqa: E402

VIEW_SQL = Path(__file__).resolve().parent.parent / "app" / "sql" / "v_tasks_ranked.sql"


def main() -> None:
    print("1) ALTER tasks ADD has_active_sprint…")
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS has_active_sprint BOOLEAN NOT NULL DEFAULT FALSE"
        ))

    print("2) Пересоздаю v_tasks_ranked…")
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL.read_text(encoding="utf-8")))

    print("3) Сидлю платформы (PowerBI, Сервис Самопланирования)…")
    with SessionLocal() as db:
        seed_platforms(db)
        db.commit()

    print("4) Контроль:")
    with engine.begin() as conn:
        col = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='v_tasks_ranked' AND column_name='has_active_sprint'"
        )).scalar()
        print(f"   v_tasks_ranked.has_active_sprint: {'OK' if col else 'НЕТ'}")
        n = conn.execute(text("SELECT count(*) FROM platforms")).scalar()
        print(f"   платформ в БД: {n}")

    print("\nГотово. Перезалейте задачи: POST /api/tasks/reload-from-file.")


if __name__ == "__main__":
    main()
