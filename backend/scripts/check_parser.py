"""Сверка парсера с эталоном ITP-3085 (response_example.json). Запуск без базы.

    python -m scripts.check_parser
Из каталога backend/ . Падает с ненулевым кодом, если есть расхождения.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.jira_mapper import JiraFieldMapper, load_issues  # noqa: E402

EXPECTED = {
    "jira_key": "ITP-3085",
    "jira_internal_id": "155677",
    "goal_type_name": "Операционная эффективность, руб.",
    "issue_type": "PI",
    "company_effect_rub": 20000000.0,
    "adjusted_ebitda": 20000000.0,
    "eta_months": 12,
    "total_story_points": 34.0,
    "ceo_priority": 2,
    "coefficient": "7",
}
EXPECTED_LABELS = {"Cognos", "DWH", "MetaSprint5", "Metasprint"}
EXPECTED_REQUIRED_PLATFORM = "Cognos/DWH"


def main() -> int:
    path = get_settings().jira_sample_path
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    issues = load_issues(payload)
    if not issues:
        print(f"FAIL: в {path} не найдено ни одной задачи")
        return 1

    task = JiraFieldMapper().to_task(issues[0])
    errors: list[str] = []

    for attr, exp in EXPECTED.items():
        got = getattr(task, attr)
        if isinstance(exp, float):
            ok = got is not None and abs(float(got) - exp) < 1e-6
        else:
            ok = got == exp
        mark = "ok " if ok else "XX "
        print(f"  {mark}{attr:<22} = {got!r}")
        if not ok:
            errors.append(f"{attr}: ждали {exp!r}, получили {got!r}")

    if set(task.labels) != EXPECTED_LABELS:
        errors.append(f"labels: ждали {EXPECTED_LABELS}, получили {set(task.labels)}")
    print(f"  -- labels = {task.labels}")

    required = [p.platform_name for p in task.platforms if p.is_required]
    print(f"  -- required platforms = {required}")
    if EXPECTED_REQUIRED_PLATFORM not in required:
        errors.append(f"platform {EXPECTED_REQUIRED_PLATFORM!r} не отмечена required")

    cognos = next((p for p in task.platforms if p.platform_name == "Cognos/DWH"), None)
    print(f"  -- Cognos/DWH estimate = {cognos.estimate_story_points if cognos else None}")
    print(f"  -- current_sprint = {task.current_sprint!r}")

    if errors:
        print("\nРАСХОЖДЕНИЯ:")
        for e in errors:
            print("  -", e)
        return 1
    print("\nOK: парсер совпал с эталоном ITP-3085")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
