import type { PlatformRef, TaskRanked } from "../types";
import { money, ratio } from "../format";

export interface Col {
  key: string;
  label: string;
  num?: boolean;
  cell: (t: TaskRanked) => string;
}

function dateShort(d: string | null): string {
  if (!d) return "";
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y.slice(2)}`;
}

// Все столбцы (как в Excel «Тетрис»). Видимость управляется меню «Колонки».
export const BASE_COLS: Col[] = [
  { key: "business_unit", label: "Business unit", cell: (t) => t.business_unit ?? "—" },
  { key: "goal_type_name", label: "Тип цели", cell: (t) => t.goal_type_name ?? "—" },
  { key: "customer_name", label: "Заказчик", cell: (t) => t.customer_name ?? "—" },
  { key: "it_business_partner", label: "IT БП", cell: (t) => t.it_business_partner ?? "—" },
  { key: "change_scope", label: "Change scope", cell: (t) => t.change_scope ?? "—" },
  { key: "task_status", label: "Статус", cell: (t) => t.task_status ?? "—" },
  { key: "end_date", label: "End date", num: true, cell: (t) => dateShort(t.end_date) },
  { key: "baseline_end_date", label: "Baseline", num: true, cell: (t) => dateShort(t.baseline_end_date) },
  { key: "eta_months", label: "ETA", num: true, cell: (t) => (t.eta_months ?? "").toString() },
  { key: "ceo_priority", label: "CEO", num: true, cell: (t) => (t.ceo_priority ?? "").toString() },
  { key: "adjusted_annual_effect", label: "Привед. эффект", num: true, cell: (t) => money(t.adjusted_annual_effect) },
  { key: "adjusted_ebitda", label: "Привед. EBITDA", num: true, cell: (t) => money(t.adjusted_ebitda) },
  { key: "ebitda_per_story_point", label: "EBITDA к SP", num: true, cell: (t) => ratio(t.ebitda_per_story_point) },
  { key: "coefficient", label: "Коэф.", num: true, cell: (t) => t.coefficient ?? "" },
  { key: "total_story_points", label: "SP", num: true, cell: (t) => (t.total_story_points ?? "—").toString() },
  { key: "max_sprints", label: "МАКС. спринтов", num: true, cell: (t) => (t.max_sprints ?? "").toString() },
  { key: "contractor_cost_rub", label: "Подрядчики, ₽", num: true, cell: (t) => (t.contractor_cost_rub ? money(t.contractor_cost_rub) : "—") },
  { key: "dod_text", label: "DoD", cell: (t) => (t.dod_text ? "есть" : "—") },
  { key: "labels", label: "Метки", cell: (t) => t.labels ?? "—" },
  { key: "platforms_required", label: "Платформы (нужны)", cell: (t) => t.platforms_required ?? "—" },
];

// Скрытые по умолчанию (тяжёлые/редкие). Платформы — отдельный ключ "__platforms".
export const DEFAULT_HIDDEN: string[] = [
  "customer_name", "it_business_partner", "change_scope", "task_status",
  "dod_text", "labels", "platforms_required", "__platforms", "__sprints",
];

export const PLATFORMS_KEY = "__platforms";
export const SPRINTS_KEY = "__sprints";

export function visibleCols(hidden: Set<string>): Col[] {
  return BASE_COLS.filter((c) => !hidden.has(c.key));
}

export function platformsVisible(hidden: Set<string>): boolean {
  return !hidden.has(PLATFORMS_KEY);
}

export function sprintsVisible(hidden: Set<string>): boolean {
  return !hidden.has(SPRINTS_KEY);
}

export function platformKey(p: PlatformRef): string {
  return `plat_${p.platform_id}`;
}

// --- ширины колонок (личное, localStorage) ---
const WIDTHS_KEY = "tetris_colwidths";
export const DEFAULT_WIDTHS: Record<string, number> = {
  __sel: 30, __key: 132, __summary: 260, __plat: 30, __sprint: 44,
  business_unit: 130, goal_type_name: 150, customer_name: 180,
  it_business_partner: 180, change_scope: 140, task_status: 90,
  end_date: 78, baseline_end_date: 78, eta_months: 50, ceo_priority: 50,
  adjusted_annual_effect: 120, adjusted_ebitda: 120, ebitda_per_story_point: 110,
  coefficient: 56, total_story_points: 56, max_sprints: 88, contractor_cost_rub: 110,
  dod_text: 60, labels: 220, platforms_required: 180,
};

export function loadWidths(): Record<string, number> {
  try {
    const raw = localStorage.getItem(WIDTHS_KEY);
    if (raw) return { ...DEFAULT_WIDTHS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { ...DEFAULT_WIDTHS };
}
export function saveWidths(w: Record<string, number>) {
  localStorage.setItem(WIDTHS_KEY, JSON.stringify(w));
}
export function colWidth(w: Record<string, number>, key: string): number {
  return w[key] ?? DEFAULT_WIDTHS[key] ?? 110;
}

// --- кастомная палитра кисти (личное, localStorage) ---
const PALETTE_KEY = "tetris_palette";
export const DEFAULT_PALETTE = ["#ffd5d5", "#fff2b3", "#c8f0d4", "#cfe2ff", "#e6d5ff", "#ffe0c2"];
export function loadPalette(): string[] {
  try {
    const raw = localStorage.getItem(PALETTE_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [...DEFAULT_PALETTE];
}
export function savePalette(p: string[]) {
  localStorage.setItem(PALETTE_KEY, JSON.stringify(p));
}


