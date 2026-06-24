"""Доводка №15: новый признак is_unplatformed — пересоздать представление.

    python -m scripts.migrate_doc15

Добавляет в v_tasks_ranked поле is_unplatformed (нет ни одной требуемой платформы).
Только пересоздание VIEW (DROP+CREATE внутри файла), таблицы не трогаются.
Запуск из каталога backend/ при поднятом PostgreSQL.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.read_models import TaskRanked  # noqa: E402,F401 (регистрирует маппинг вьюхи)

VIEW_SQL = Path(__file__).resolve().parent.parent / "app" / "sql" / "v_tasks_ranked.sql"


def main() -> None:
    print("1) Пересоздаю представление v_tasks_ranked (с is_unplatformed)…")
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL.read_text(encoding="utf-8")))

    print("2) Контроль (колонка в представлении):")
    with engine.begin() as conn:
        col = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='v_tasks_ranked' AND column_name='is_unplatformed'"
        )).scalar()
        print(f"   v_tasks_ranked.is_unplatformed: {'OK' if col else 'НЕТ'}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
