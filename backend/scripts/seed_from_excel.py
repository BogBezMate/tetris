"""Загрузить несколько реальных задач из листа «Автовыгрузка» (Макет тетрис.xlsx).

Временные данные для разработки, пока куратор не прислал JSON. upsert по jira_key.

    python -m scripts.seed_from_excel [N]   (по умолчанию 8 задач)

Запуск из backend/ при поднятом PostgreSQL и заполненных справочниках (bootstrap).
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openpyxl  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import GoalType, Platform, Task, TaskLabel, TaskPlatform  # noqa: E402

EXCEL = Path(__file__).resolve().parent.parent.parent / "Макет тетрис.xlsx"

# индекс колонки (0-based) -> платформа; V…AL = столбцы 21…37
PLATFORM_COLS = {
    21: "1С ЗУП", 22: "1С ERP", 23: "1С POS", 24: "1С WMS", 25: "1С А Контур",
    26: "Askona.ru", 27: "BPMSoft", 28: "Cognos/DWH", 29: "Directum",
    30: "Аналитика IT BP", 31: "Галактика", 32: "Инфраструктура", 33: "СНГ",
    34: "WebTutor", 35: "PIM/MDM", 36: "MP", 37: "OMNI",
}
# названия платформ из поля Platform (S, индекс 18) пишут чуть иначе — нормализуем
PLATFORM_ALIASES = {
    "1c зуп": "1С ЗУП", "1с зуп": "1С ЗУП", "галактика": "Галактика",
    "галактики": "Галактика", "команда снг": "СНГ", "снг": "СНГ",
    "инфраструктура": "Инфраструктура", "cognos/dwh": "Cognos/DWH",
}


def as_date(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def norm_platform(name: str) -> str | None:
    n = name.strip()
    return PLATFORM_ALIASES.get(n.lower(), n)


def main(limit: int = 8) -> None:
    wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
    ws = wb["Автовыгрузка"]

    with SessionLocal() as db:
        goals = {g.goal_type_name: g.goal_type_id for g in db.scalars(select(GoalType))}
        plats = {p.platform_name: p.platform_id for p in db.scalars(select(Platform))}
        loaded = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            key = row[0]
            if not key or not str(key).startswith("ITP-"):
                continue

            goal_name = (row[7] or "").strip() if row[7] else None
            # «Снижение рисков, руб.» в Excel, у нас «Снижение рисков» — берём как есть, матч по имени
            goal_id = goals.get(goal_name)

            task = db.scalar(select(Task).where(Task.jira_key == str(key)))
            if task is None:
                task = Task(jira_key=str(key), jira_internal_id=f"xlsx-{key}")
                db.add(task)

            task.business_unit = row[1]
            task.change_scope = row[2]
            task.task_summary = (row[3] or "").strip() if row[3] else None
            task.customer_name = row[4]
            task.it_business_partner = row[5]
            task.task_status = row[6]
            task.goal_type_id = goal_id
            task.company_effect_rub = num(row[8])
            task.end_date = as_date(row[9])
            task.baseline_end_date = as_date(row[10])
            task.eta_months = int(num(row[12])) if num(row[12]) else None
            task.ceo_priority = int(num(row[13])) if num(row[13]) else None
            task.adjusted_ebitda = num(row[15])
            task.coefficient = str(row[17]) if row[17] not in (None, "") else None
            task.total_story_points = num(row[19])
            task.contractor_cost_rub = num(row[20])
            task.issue_type = "PI"

            # требуемые платформы из поля Platform (S = индекс 18)
            required = set()
            if row[18]:
                for part in str(row[18]).split(","):
                    np = norm_platform(part)
                    if np:
                        required.add(np)

            task.platforms.clear()
            task.labels.clear()
            db.flush()  # удалить старые связи до вставки новых (unique constraints)
            for col, pname in PLATFORM_COLS.items():
                est = num(row[col]) if col < len(row) else None
                is_req = pname in required
                if est is None and not is_req:
                    continue
                pid = plats.get(pname)
                if pid:
                    task.platforms.append(TaskPlatform(
                        platform_id=pid, is_required=is_req, estimate_story_points=est
                    ))

            # Метки. Для разнообразия колодцев в демо переопределяем спринт-метку по индексу:
            # 0→MetaSprint, 1→AlphaSprint, 2→OpenSprint, 3→без спринт-метки (To be allocated).
            raw_labels = [
                s.strip() for s in str(row[11] or "").split(",")
                if s.strip() and "sprint" not in s.strip().lower()
            ]
            demo_zone = ["MetaSprint", "AlphaSprint", "OpenSprint", None][loaded % 4]
            if demo_zone:
                raw_labels.insert(0, demo_zone)
            for lbl in dict.fromkeys(raw_labels):
                task.labels.append(TaskLabel(label_name=lbl))

            loaded += 1
            if loaded >= limit:
                break

        db.commit()
        print(f"Загружено задач из Excel: {loaded}")
    wb.close()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    main(n)
