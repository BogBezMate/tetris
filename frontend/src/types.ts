export type Role = "editor" | "reader";

export interface User {
  user_id: number;
  user_email: string;
  full_name: string | null;
  user_role: Role;
}

export interface TaskRanked {
  task_id: number;
  jira_key: string;
  task_summary: string | null;
  issue_type: string | null;
  task_status: string | null;
  business_unit: string | null;
  change_scope: string | null;
  customer_name: string | null;
  it_business_partner: string | null;
  dod_text: string | null;
  goal_type_name: string | null;
  company_effect_rub: number | null;
  eta_months: number | null;
  adjusted_ebitda: number | null;
  total_story_points: number | null;
  contractor_cost_rub: number | null;
  coefficient: string | null;
  ceo_priority: number | null;
  current_sprint: string | null;
  end_date: string | null;
  baseline_end_date: string | null;
  labels: string | null;
  platforms_required: string | null;
  adjusted_annual_effect: number;
  ebitda_per_story_point: number;
  is_underestimated: boolean;
  is_unplatformed: boolean;
  has_estimate_no_team: boolean;
  has_unselected_estimate: boolean;
  has_active_sprint: boolean;
  max_sprints: number;
  max_sprints_override: number | null;
}

export interface PlatformRef {
  platform_id: number;
  platform_name: string;
  sp_per_sprint: number;
}

export interface GridRow {
  task: TaskRanked;
  zone_id: number | null;
  plan_item_id: number | null;
  item_position: number;
  platform_estimates: Record<string, number>;
  overridden_platforms?: number[];
}

export interface Grid {
  plan: Plan;
  platforms: PlatformRef[];
  zones: Zone[];
  rows: GridRow[];
  presentation: Presentation | null;
  velocity_per_meta?: Record<string, number>;
}

export interface QuarterVelocity {
  platform_id: number;
  platform_name: string;
  capacity_sp: number | null;
  sp_per_sprint: number | null;        // делитель этого метаспринта (null = дефолт)
  sp_per_sprint_default: number;       // глобальный дефолт (для placeholder)
}

export interface AutoRow {
  task: TaskRanked;
  zone_name: string;
  in_plan: boolean;
  platform_estimates: Record<string, number>;
}
export interface AutoData {
  platforms: PlatformRef[];
  rows: AutoRow[];
}

export interface Zone {
  zone_id: number;
  zone_name: string;
}

export interface Quarter {
  quarter_id: number;
  quarter_name: string;
  quarter_year: number;
  quarter_number: number;
}

export interface Plan {
  plan_id: number;
  quarter_id: number;
  plan_name: string;
  plan_status: string;
  created_at: string;
  updated_at: string | null;
  presentation: Presentation | null;
}

export interface GoalType {
  goal_type_id: number;
  goal_type_name: string;
  affects_effect: boolean;
}

export interface Note {
  id: string;
  text: string;
  bold?: boolean;
  fill?: string;
}
export interface Presentation {
  order?: string[];                          // "t:<taskId>" | "n:<noteId>" — порядок строк
  notes?: Note[];                            // строки-заметки
  row_fills?: Record<string, string>;        // taskId -> цвет всей строки
  cell_fills?: Record<string, string>;       // "taskId:colKey" -> цвет ячейки (кисть)
}

export interface PlanItem {
  plan_item_id: number;
  task_id: number;
  zone_id: number;
  item_position: number;
  task: TaskRanked | null;
}

export interface BoardColumn {
  zone_id: number;
  zone_name: string;
  items: PlanItem[];
}

export interface Board {
  plan: Plan;
  columns: BoardColumn[];
}
