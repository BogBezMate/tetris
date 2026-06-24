from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --- Справочники -----------------------------------------------------------

class GoalType(Base):
    __tablename__ = "goal_types"

    goal_type_id: Mapped[int] = mapped_column(primary_key=True)
    goal_type_name: Mapped[str] = mapped_column(String(120), unique=True)
    affects_effect: Mapped[bool] = mapped_column(Boolean, default=False)

    tasks: Mapped[list[Task]] = relationship(back_populates="goal_type")


class Platform(Base):
    __tablename__ = "platforms"

    platform_id: Mapped[int] = mapped_column(primary_key=True)
    platform_name: Mapped[str] = mapped_column(String(120), unique=True)
    jira_field_id: Mapped[str] = mapped_column(String(40), unique=True)
    # Velocity: сколько SP в спринт «откусываем» от задачи (делитель из Excel, строка 2).
    sp_per_sprint: Mapped[float] = mapped_column(Numeric(6, 2), default=5, server_default="5")


class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[int] = mapped_column(primary_key=True)
    zone_name: Mapped[str] = mapped_column(String(60), unique=True)


# --- Данные из Jira --------------------------------------------------------

class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(primary_key=True)
    jira_key: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    jira_internal_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    goal_type_id: Mapped[int | None] = mapped_column(ForeignKey("goal_types.goal_type_id"))

    task_summary: Mapped[str | None] = mapped_column(Text)
    issue_type: Mapped[str | None] = mapped_column(String(40))
    task_status: Mapped[str | None] = mapped_column(String(60))
    business_unit: Mapped[str | None] = mapped_column(String(120))
    change_scope: Mapped[str | None] = mapped_column(Text)
    customer_name: Mapped[str | None] = mapped_column(String(200))
    it_business_partner: Mapped[str | None] = mapped_column(String(200))
    ceo_priority: Mapped[int | None] = mapped_column(Integer)
    dod_text: Mapped[str | None] = mapped_column(Text)
    # Ручной максимум спринтов: NULL/0 = считается автоматически (ROUNDUP(MAX(оценка/velocity))).
    max_sprints_override: Mapped[int | None] = mapped_column(Integer)

    company_effect_rub: Mapped[float | None] = mapped_column(Numeric(20, 4))
    eta_months: Mapped[int | None] = mapped_column(Integer)
    adjusted_ebitda: Mapped[float | None] = mapped_column(Numeric(20, 4))
    total_story_points: Mapped[float | None] = mapped_column(Numeric(10, 2))
    contractor_cost_rub: Mapped[float | None] = mapped_column(Numeric(20, 4))
    coefficient: Mapped[str | None] = mapped_column(String(50))

    current_sprint: Mapped[str | None] = mapped_column(String(200))
    # есть ли у задачи спринт со state=ACTIVE → колодец OpenSprint
    has_active_sprint: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    end_date: Mapped[date | None] = mapped_column(Date)
    baseline_end_date: Mapped[date | None] = mapped_column(Date)

    jira_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    goal_type: Mapped[GoalType | None] = relationship(back_populates="tasks")
    platforms: Mapped[list[TaskPlatform]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    labels: Mapped[list[TaskLabel]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class TaskPlatform(Base):
    __tablename__ = "task_platforms"
    __table_args__ = (UniqueConstraint("task_id", "platform_id", name="uq_task_platform"),)

    task_platform_id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"))
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.platform_id"))
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    estimate_story_points: Mapped[float | None] = mapped_column(Numeric(10, 2))

    task: Mapped[Task] = relationship(back_populates="platforms")
    platform: Mapped[Platform] = relationship()


class TaskLabel(Base):
    __tablename__ = "task_labels"
    __table_args__ = (UniqueConstraint("task_id", "label_name", name="uq_task_label"),)

    label_id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"))
    label_name: Mapped[str] = mapped_column(String(120))

    task: Mapped[Task] = relationship(back_populates="labels")


class JiraSyncLog(Base):
    __tablename__ = "jira_sync_log"

    sync_log_id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.task_id", ondelete="SET NULL"))
    sync_direction: Mapped[str] = mapped_column(String(20))  # 'in' | 'out'
    sync_payload: Mapped[dict | None] = mapped_column(JSON)
    sync_status: Mapped[str] = mapped_column(String(20))  # 'ok' | 'error'
    sync_error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Планирование и доступ -------------------------------------------------

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    full_name: Mapped[str | None] = mapped_column(String(200))
    user_role: Mapped[str] = mapped_column(String(20), default="reader")  # 'editor' | 'reader'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Quarter(Base):
    __tablename__ = "quarters"

    quarter_id: Mapped[int] = mapped_column(primary_key=True)
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    quarter_name: Mapped[str] = mapped_column(String(60))
    quarter_year: Mapped[int] = mapped_column(Integer)
    quarter_number: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    plans: Mapped[list[Plan]] = relationship(back_populates="quarter")
    velocities: Mapped[list[QuarterVelocity]] = relationship(
        back_populates="quarter", cascade="all, delete-orphan"
    )


class Plan(Base):
    __tablename__ = "plans"

    plan_id: Mapped[int] = mapped_column(primary_key=True)
    quarter_id: Mapped[int] = mapped_column(ForeignKey("quarters.quarter_id"))
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    plan_name: Mapped[str] = mapped_column(String(120))
    plan_status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|approved|archived
    presentation: Mapped[dict | None] = mapped_column(JSON)  # Excel-слой: заливки, заметки
    # Снимок данных таблицы плана на момент утверждения (историчность). NULL у черновика.
    approved_snapshot: Mapped[dict | None] = mapped_column(JSON)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    quarter: Mapped[Quarter] = relationship(back_populates="plans")
    items: Mapped[list[PlanItem]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    estimate_overrides: Mapped[list[PlanTaskEstimate]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )


class PlanItem(Base):
    __tablename__ = "plan_items"
    __table_args__ = (UniqueConstraint("plan_id", "task_id", name="uq_plan_task"),)

    plan_item_id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.plan_id", ondelete="CASCADE"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id"))
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.zone_id"))
    added_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    item_position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    plan: Mapped[Plan] = relationship(back_populates="items")
    task: Mapped[Task] = relationship()
    zone: Mapped[Zone] = relationship()


class QuarterVelocity(Base):
    """Velocity платформы внутри метаспринта (задаётся вручную). Два числа:

    - capacity_sp — ёмкость за метаспринт (Velocity per Meta); сравнивается со спросом
      (суммой оценок плана) для подсветки перегруза;
    - sp_per_sprint — делитель «SP за спринт» для этого метаспринта (колонки «спринты»
      = оценка ÷ делитель, «МАКС спринтов»). NULL → берётся глобальный Platform.sp_per_sprint.
    """
    __tablename__ = "quarter_velocities"
    __table_args__ = (
        UniqueConstraint("quarter_id", "platform_id", name="uq_quarter_platform_velocity"),
    )

    quarter_velocity_id: Mapped[int] = mapped_column(primary_key=True)
    quarter_id: Mapped[int] = mapped_column(
        ForeignKey("quarters.quarter_id", ondelete="CASCADE")
    )
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.platform_id"))
    capacity_sp: Mapped[float | None] = mapped_column(Numeric(10, 2))
    sp_per_sprint: Mapped[float | None] = mapped_column(Numeric(6, 2))

    quarter: Mapped[Quarter] = relationship(back_populates="velocities")
    platform: Mapped[Platform] = relationship()


class PlanTaskEstimate(Base):
    """Остаточная оценка задачи по платформе В РАМКАХ плана.

    Переопределяет оценку из Jira (task_platforms.estimate_story_points) только
    для конкретного плана. «Сброс к Jira» = удалить эту запись.
    """
    __tablename__ = "plan_task_estimates"
    __table_args__ = (
        UniqueConstraint("plan_id", "task_id", "platform_id", name="uq_plan_task_platform"),
    )

    plan_task_estimate_id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.plan_id", ondelete="CASCADE"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.task_id", ondelete="CASCADE"))
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.platform_id"))
    estimate_sp: Mapped[float | None] = mapped_column(Numeric(10, 2))

    plan: Mapped[Plan] = relationship(back_populates="estimate_overrides")
