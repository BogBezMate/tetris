"""Поднять базу с нуля для локальной разработки одной командой.

    python -m scripts.bootstrap

Делает: создаёт таблицы и представление, заполняет справочники, грузит задачи из
response_example.json, заводит двух пользователей (editor/reader). Идемпотентно по
справочникам и пользователям. Запуск из каталога backend/ при поднятом PostgreSQL.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.read_models import TaskRanked  # noqa: E402  (регистрирует маппинг вьюхи)
from app.seeds import seed_all  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.services.jira_sync import JiraSyncService  # noqa: E402

VIEW_SQL = (Path(__file__).resolve().parent.parent / "app" / "sql" / "v_tasks_ranked.sql")

DEFAULT_USERS = [
    ("editor@askona.ru", "editor123", "Редактор Тетрис", "editor"),
    ("reader@askona.ru", "reader123", "Читатель Тетрис", "reader"),
]


def main() -> None:
    print("1) Создаю таблицы…")
    Base.metadata.create_all(bind=engine, tables=[
        t for t in Base.metadata.sorted_tables if t.name != "v_tasks_ranked"
    ])

    print("2) Создаю представление v_tasks_ranked…")
    with engine.begin() as conn:
        conn.execute(text(VIEW_SQL.read_text(encoding="utf-8")))

    with SessionLocal() as db:
        print("3) Заполняю справочники…")
        seed_all(db)

        print("4) Граблю задачи из файла…")
        stats = JiraSyncService(db).load_from_file()
        print(f"   загружено: {stats}")

        print("5) Завожу пользователей…")
        auth = AuthService(db)
        for email, pwd, name, role in DEFAULT_USERS:
            if not auth.get_by_email(email):
                auth.create_user(email, pwd, name, role)
                print(f"   + {email} / {pwd}  ({role})")
            else:
                print(f"   уже есть: {email}")

    print("\nГотово. Запуск API:  uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
