"""Офлайн smoke-тест всего DB-потока на SQLite в памяти — без PostgreSQL.

Прогоняет реальные seeds + loader + представление и проверяет метрики на ITP-3085.
Это проверка логики на время разработки; боевая СУБД — PostgreSQL (bootstrap.py).

    python -m scripts.smoke_sqlite
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402
from app.read_models import TaskRanked  # noqa: E402
from app.seeds import seed_all  # noqa: E402
from app.services import loader  # noqa: E402

VIEW_SQL = Path(__file__).resolve().parent.parent / "app" / "sql" / "v_tasks_ranked.sql"


def main() -> int:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)

    Base.metadata.create_all(bind=engine, tables=[
        t for t in Base.metadata.sorted_tables if t.name != "v_tasks_ranked"
    ])
    view_sql = VIEW_SQL.read_text(encoding="utf-8").replace(
        "CREATE OR REPLACE VIEW", "CREATE VIEW"
    )
    with engine.begin() as conn:
        conn.execute(text(view_sql))

    payload = json.loads(get_settings().jira_sample_path.read_text(encoding="utf-8"))

    with Session() as db:
        seed_all(db)
        stats = loader.load_payload(db, payload)
        print(f"loader: {stats}")

        row = db.scalar(select(TaskRanked).where(TaskRanked.jira_key == "ITP-3085"))
        assert row is not None, "ITP-3085 не загрузилась"

        # Допуск великоват намеренно: у SQLite нет типа NUMERIC, деление идёт
        # целочисленно (20000000/12*12 -> 19999992, 20000000/34 -> 588235).
        # Проверяем правильность ЛОГИКИ; точные десятичные — на PostgreSQL (bootstrap).
        checks = {
            "adjusted_annual_effect": (float(row.adjusted_annual_effect), 20_000_000.0, 20.0),
            "ebitda_per_story_point": (float(row.ebitda_per_story_point), 20_000_000 / 34, 1.0),
            "max_sprints": (float(row.max_sprints), 34.0, 0.01),
        }
        errors = []
        for name, (got, exp, tol) in checks.items():
            ok = abs(got - exp) <= tol
            print(f"  {'ok ' if ok else 'XX '}{name:<24} = {got:,.2f}  (ждали ~{exp:,.2f})")
            if not ok:
                errors.append(name)

        und = bool(row.is_underestimated)
        print(f"  {'ok ' if und is False else 'XX '}is_underestimated        = {und}  (ждали False)")
        if und is not False:
            errors.append("is_underestimated")

    if errors:
        print("\nРАСХОЖДЕНИЯ:", errors)
        return 1
    print("\nOK: весь DB-поток (seed -> load -> view) сошёлся на ITP-3085")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
