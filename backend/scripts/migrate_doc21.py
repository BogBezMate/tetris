"""Доводка №21: снимок данных утверждённого плана (историчность).

    python -m scripts.migrate_doc21

Добавляет колонку plans.approved_snapshot (JSON) — снимок таблицы плана на момент
утверждения. Только ALTER, представление не трогаем.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402

DDL = ["ALTER TABLE plans ADD COLUMN IF NOT EXISTS approved_snapshot JSON"]


def main() -> None:
    print("1) ALTER plans ADD approved_snapshot…")
    with engine.begin() as conn:
        for sql in DDL:
            conn.execute(text(sql))
    print("2) Контроль:")
    with engine.begin() as conn:
        col = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='plans' AND column_name='approved_snapshot'"
        )).scalar()
        print(f"   plans.approved_snapshot: {'OK' if col else 'НЕТ'}")
    print("\nГотово.")


if __name__ == "__main__":
    main()
