"""Доводка №17: признак has_unselected_estimate — пересоздать представление.

    python -m scripts.migrate_doc17

Добавляет в v_tasks_ranked поле has_unselected_estimate
(есть оценка у платформы, которую не выбрали как требуемую).
Только пересоздание VIEW, таблицы не трогаются.
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
    print("1) Пересоздаю представление v_tasks_ranked (с has_unselected_estimate)…")
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL.read_text(encoding="utf-8")))

    print("2) Контроль (колонка в представлении):")
    with engine.begin() as conn:
        col = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='v_tasks_ranked' AND column_name='has_unselected_estimate'"
        )).scalar()
        print(f"   v_tasks_ranked.has_unselected_estimate: {'OK' if col else 'НЕТ'}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
