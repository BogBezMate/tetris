"""JiraFieldMapper — превращает JSON задачи Jira в плоскую структуру ParsedTask.

Не зависит от базы: на выходе dataclass, который загрузчик (этап 5) кладёт в ORM.
Здесь собрано всё знание о customfield-полях, разборе спринта и платформ.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from app import jira_fields as jf

_SPRINT_STATE_RE = re.compile(r"state=([^,\]]+)")
_SPRINT_NAME_RE = re.compile(r"name=([^,\]]+)")


@dataclass
class ParsedPlatform:
    platform_name: str
    jira_field_id: str
    is_required: bool
    estimate_story_points: float | None


@dataclass
class ParsedTask:
    jira_key: str
    jira_internal_id: str
    goal_type_name: str | None = None
    task_summary: str | None = None
    issue_type: str | None = None
    task_status: str | None = None
    business_unit: str | None = None
    change_scope: str | None = None
    customer_name: str | None = None
    it_business_partner: str | None = None
    ceo_priority: int | None = None
    dod_text: str | None = None
    company_effect_rub: float | None = None
    eta_months: int | None = None
    adjusted_ebitda: float | None = None
    total_story_points: float | None = None
    contractor_cost_rub: float | None = None
    coefficient: str | None = None
    current_sprint: str | None = None
    has_active_sprint: bool = False
    end_date: date | None = None
    baseline_end_date: date | None = None
    jira_updated_at: datetime | None = None
    platforms: list[ParsedPlatform] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


def _num(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value) -> int | None:
    n = _num(value)
    return int(n) if n is not None else None


def _opt_value(value) -> str | None:
    """Поле-選 option: {'value': 'X'} -> 'X'. Иначе строка/None."""
    if isinstance(value, dict):
        return value.get("value")
    if isinstance(value, str):
        return value or None
    return None


def _first_opt_value(value) -> str | None:
    """Массив option-ов: [{'value': '12'}] -> '12'."""
    if isinstance(value, list) and value:
        return _opt_value(value[0])
    return _opt_value(value)


def _person_name(value) -> str | None:
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name")
    if isinstance(value, str):
        return value or None
    return None


def _as_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _as_datetime(value) -> datetime | None:
    if not value:
        return None
    raw = str(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _active_sprint_name(value) -> str | None:
    """Из массива «грязных» greenhopper-строк берём имя ACTIVE-спринта.

    Если активного нет — имя последнего из списка (fallback, как ориентир).
    Допущение: имя спринта не содержит запятых (в данных ITP так и есть).
    """
    if not value:
        return None
    items = value if isinstance(value, list) else [value]
    last_name: str | None = None
    for raw in items:
        s = str(raw)
        name_m = _SPRINT_NAME_RE.search(s)
        if not name_m:
            continue
        name = name_m.group(1).strip()
        last_name = name
        state_m = _SPRINT_STATE_RE.search(s)
        if state_m and state_m.group(1).strip().upper() == "ACTIVE":
            return name
    return last_name


def _has_active_sprint(value) -> bool:
    """True, если хотя бы у одного спринта задачи state=ACTIVE (→ колодец OpenSprint)."""
    if not value:
        return False
    for raw in (value if isinstance(value, list) else [value]):
        m = _SPRINT_STATE_RE.search(str(raw))
        if m and m.group(1).strip().upper() == "ACTIVE":
            return True
    return False


class JiraFieldMapper:
    """Разбирает одну задачу Jira (issue dict) в ParsedTask."""

    def to_task(self, issue: dict) -> ParsedTask:
        f: dict = issue.get("fields") or {}

        change_scope_raw = f.get(jf.CF_CHANGE_SCOPE)
        change_scope = (
            ", ".join(str(x) for x in change_scope_raw)
            if isinstance(change_scope_raw, list)
            else (change_scope_raw or None)
        )

        parsed = ParsedTask(
            jira_key=issue["key"],
            jira_internal_id=str(issue["id"]),
            goal_type_name=_opt_value(f.get(jf.CF_GOAL_TYPE)),
            task_summary=f.get("summary"),
            issue_type=(f.get("issuetype") or {}).get("name"),
            task_status=(f.get("status") or {}).get("name"),
            business_unit=_opt_value(f.get(jf.CF_BUSINESS_UNIT)),
            change_scope=change_scope,
            customer_name=_person_name(f.get("customfield_10811")),
            it_business_partner=_person_name(f.get("customfield_10812")),
            ceo_priority=_int(f.get(jf.CF_CEO_PRIORITY)),
            dod_text=f.get(jf.CF_DOD),
            company_effect_rub=_num(f.get(jf.CF_COMPANY_EFFECT)),
            eta_months=_int(_first_opt_value(f.get(jf.CF_ETA_MONTHS))),
            adjusted_ebitda=_num(f.get(jf.CF_ADJUSTED_EBITDA)),
            total_story_points=_num(f.get(jf.CF_STORY_POINTS)),
            contractor_cost_rub=_num(f.get(jf.CF_CONTRACTOR_COST)),
            coefficient=_opt_value(f.get(jf.CF_COEFFICIENT)),
            current_sprint=_active_sprint_name(f.get(jf.CF_SPRINT)),
            has_active_sprint=_has_active_sprint(f.get(jf.CF_SPRINT)),
            end_date=_as_date(f.get(jf.CF_END_DATE)),
            baseline_end_date=_as_date(f.get(jf.CF_BASELINE_END_DATE)),
            jira_updated_at=_as_datetime(f.get("updated")),
            labels=list(f.get("labels") or []),
        )

        required: set[str] = set()
        for v in (f.get(jf.CF_PLATFORM_SELECTOR) or []):
            raw = _opt_value(v)
            if raw is None:
                continue
            name = jf.PLATFORM_ALIASES.get(raw, raw)  # нормализуем написание
            if name in jf.PLATFORM_IGNORE:
                continue  # не платформа (нет оценок/справочника)
            required.add(name)
        for name, cf_id in jf.PLATFORM_FIELDS.items():
            estimate = _num(f.get(cf_id))
            is_required = name in required
            if not is_required and estimate is None:
                continue  # платформа не нужна и без оценки — не храним
            parsed.platforms.append(
                ParsedPlatform(
                    platform_name=name,
                    jira_field_id=cf_id,
                    is_required=is_required,
                    estimate_story_points=estimate,
                )
            )
        return parsed


def load_issues(payload) -> list[dict]:
    """Достаёт список issue из разных форматов выгрузки Jira."""
    if isinstance(payload, dict):
        if "issues" in payload:
            return payload["issues"]
        if "fields" in payload:
            return [payload]
        if "issue" in payload:  # формат вебхука
            return [payload["issue"]]
    if isinstance(payload, list):
        return payload
    return []
