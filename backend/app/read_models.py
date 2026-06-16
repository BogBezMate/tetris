"""Классы только на чтение, отображённые на представление базы.

TaskRanked не создаёт таблицу — он маппится на v_tasks_ranked (создаётся миграцией).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class TaskRanked(Base):
    __tablename__ = "v_tasks_ranked"
    __table_args__ = {"info": {"is_view": True}}

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jira_key: Mapped[str] = mapped_column(String)
    jira_internal_id: Mapped[str] = mapped_column(String)
    task_summary: Mapped[str | None] = mapped_column(Text)
    issue_type: Mapped[str | None] = mapped_column(String)
    task_status: Mapped[str | None] = mapped_column(String)
    business_unit: Mapped[str | None] = mapped_column(String)
    change_scope: Mapped[str | None] = mapped_column(Text)
    customer_name: Mapped[str | None] = mapped_column(String)
    it_business_partner: Mapped[str | None] = mapped_column(String)
    dod_text: Mapped[str | None] = mapped_column(Text)
    goal_type_id: Mapped[int | None] = mapped_column(Integer)
    goal_type_name: Mapped[str | None] = mapped_column(String)
    company_effect_rub: Mapped[float | None] = mapped_column(Numeric)
    eta_months: Mapped[int | None] = mapped_column(Integer)
    adjusted_ebitda: Mapped[float | None] = mapped_column(Numeric)
    total_story_points: Mapped[float | None] = mapped_column(Numeric)
    contractor_cost_rub: Mapped[float | None] = mapped_column(Numeric)
    coefficient: Mapped[str | None] = mapped_column(String)
    ceo_priority: Mapped[int | None] = mapped_column(Integer)
    current_sprint: Mapped[str | None] = mapped_column(String)
    end_date: Mapped[date | None] = mapped_column(Date)
    baseline_end_date: Mapped[date | None] = mapped_column(Date)
    max_sprints_override: Mapped[int | None] = mapped_column(Integer)
    labels: Mapped[str | None] = mapped_column(String)
    platforms_required: Mapped[str | None] = mapped_column(String)
    adjusted_annual_effect: Mapped[float] = mapped_column(Numeric)
    ebitda_per_story_point: Mapped[float] = mapped_column(Numeric)
    is_underestimated: Mapped[bool] = mapped_column(Boolean)
    max_sprints: Mapped[float] = mapped_column(Numeric)
