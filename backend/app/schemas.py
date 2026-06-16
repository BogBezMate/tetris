from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth ------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    user_id: int
    user_email: str
    full_name: str | None = None
    user_role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --- Tasks / метрики -------------------------------------------------------

class PlatformOut(ORMModel):
    platform_name: str
    is_required: bool
    estimate_story_points: float | None = None

class TaskRankedOut(ORMModel):
    task_id: int
    jira_key: str
    task_summary: str | None = None
    issue_type: str | None = None
    task_status: str | None = None
    business_unit: str | None = None
    change_scope: str | None = None
    customer_name: str | None = None
    it_business_partner: str | None = None
    dod_text: str | None = None
    goal_type_name: str | None = None
    company_effect_rub: float | None = None
    eta_months: int | None = None
    adjusted_ebitda: float | None = None
    total_story_points: float | None = None
    contractor_cost_rub: float | None = None
    coefficient: str | None = None
    ceo_priority: int | None = None
    current_sprint: str | None = None
    end_date: date | None = None
    baseline_end_date: date | None = None
    labels: str | None = None
    platforms_required: str | None = None
    adjusted_annual_effect: float
    ebitda_per_story_point: float
    is_underestimated: bool
    max_sprints: float
    max_sprints_override: int | None = None


class PlatformRef(ORMModel):
    platform_id: int
    platform_name: str
    sp_per_sprint: float = 5


class PlatformEstimateIn(BaseModel):
    platform_id: int
    estimate_story_points: float | None = None
    is_required: bool | None = None


class PlatformVelocityIn(BaseModel):
    platform_id: int
    sp_per_sprint: float


class TaskUpdate(BaseModel):
    """Редактирование задачи в нашей БД (все поля до записи в Jira)."""
    jira_key: str | None = None
    task_summary: str | None = None
    business_unit: str | None = None
    change_scope: str | None = None
    customer_name: str | None = None
    it_business_partner: str | None = None
    task_status: str | None = None
    issue_type: str | None = None
    goal_type_id: int | None = None
    company_effect_rub: float | None = None
    eta_months: int | None = None
    adjusted_ebitda: float | None = None
    total_story_points: float | None = None
    contractor_cost_rub: float | None = None
    coefficient: str | None = None
    ceo_priority: int | None = None
    current_sprint: str | None = None
    dod_text: str | None = None
    end_date: date | None = None
    baseline_end_date: date | None = None
    max_sprints_override: int | None = None
    platform_estimates: list[PlatformEstimateIn] | None = None


class GridRow(BaseModel):
    task: TaskRankedOut
    zone_id: int | None = None
    plan_item_id: int | None = None
    item_position: int = 0
    # оценки по платформам: platform_id -> story points
    platform_estimates: dict[int, float] = {}


class GridOut(BaseModel):
    plan: "PlanOut"
    platforms: list[PlatformRef]
    zones: list["ZoneOut"]
    rows: list[GridRow]
    presentation: dict | None = None


class AutoRow(BaseModel):
    task: TaskRankedOut
    zone_name: str
    in_plan: bool = False
    platform_estimates: dict[int, float] = {}


class AutoOut(BaseModel):
    platforms: list[PlatformRef]
    rows: list[AutoRow]


class AddTaskIn(BaseModel):
    task_id: int


class ReorderIn(BaseModel):
    task_ids: list[int]


class GoalTypeOut(ORMModel):
    goal_type_id: int
    goal_type_name: str
    affects_effect: bool


class PresentationIn(BaseModel):
    data: dict


# --- Планирование ----------------------------------------------------------

class QuarterCreate(BaseModel):
    quarter_name: str
    quarter_year: int
    quarter_number: int = Field(ge=1, le=4)
    start_date: date | None = None
    end_date: date | None = None


class QuarterOut(ORMModel):
    quarter_id: int
    quarter_name: str
    quarter_year: int
    quarter_number: int
    start_date: date | None = None
    end_date: date | None = None


class PlanCreate(BaseModel):
    quarter_id: int
    plan_name: str | None = None


class PlanOut(ORMModel):
    plan_id: int
    quarter_id: int
    plan_name: str
    plan_status: str
    created_at: datetime
    updated_at: datetime | None = None
    presentation: dict | None = None


class ZoneOut(ORMModel):
    zone_id: int
    zone_name: str


class PlanItemOut(BaseModel):
    plan_item_id: int
    task_id: int
    zone_id: int
    item_position: int
    task: TaskRankedOut | None = None


class BoardColumn(BaseModel):
    zone_id: int
    zone_name: str
    items: list[PlanItemOut]


class BoardOut(BaseModel):
    plan: PlanOut
    columns: list[BoardColumn]


class PlanItemPlacement(BaseModel):
    task_id: int
    zone_id: int
    item_position: int = 0


class SavePlacementRequest(BaseModel):
    items: list[PlanItemPlacement]
