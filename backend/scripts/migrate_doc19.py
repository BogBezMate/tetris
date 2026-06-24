"""Доводка №19: 4 непересекающихся признака качества оценки — пересоздать представление.

    python -m scripts.migrate_doc19

Переопределяет is_unplatformed (теперь = нет команд И нет оценок) и has_unselected_estimate
(теперь = есть команды + оценка у невыбранной), добавляет has_estimate_no_team
(нет команд, но есть оценка). Только пересоздание VIEW.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402
from app.read_models import TaskRanked  # noqa: E402,F401

VIEW_SQL = Path(__file__).resolve().parent.parent / "app" / "sql" / "v_tasks_ranked.sql"


def main() -> None:
    print("1) Пересоздаю v_tasks_ranked (4 признака качества оценки)…")
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL.read_text(encoding="utf-8")))

    print("2) Контроль (новая колонка has_estimate_no_team):")
    with engine.begin() as conn:
        col = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='v_tasks_ranked' AND column_name='has_estimate_no_team'"
        )).scalar()
        print(f"   has_estimate_no_team: {'OK' if col else 'НЕТ'}")

    print("\nГотово.")


if __name__ == "__main__":
    main()
