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
  { key: "company_effect_rub", label: "Эффект для компании", num: true, cell: (t) => money(t.company_effect_rub) },
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

// --- порядок столбцов (личное, localStorage; не в БД) ---
const COLORDER_KEY = "tetris_colorder";
export function loadColOrder(): string[] {
  try {
    const raw = localStorage.getItem(COLORDER_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}
export function saveColOrder(order: string[]) {
  localStorage.setItem(COLORDER_KEY, JSON.stringify(order));
}
/** Полный порядок всех колонок: сохранённые сначала, новые/недостающие — в конец в исходном порядке. */
export function fullColOrder(order: string[]): string[] {
  const all = BASE_COLS.map((c) => c.key);
  const known = order.filter((k) => all.includes(k));
  const missing = all.filter((k) => !known.includes(k));
  return [...known, ...missing];
}
/** Переместить столбец dragKey на позицию overKey, вернуть новый полный порядок. */
export function reorderCols(order: string[], dragKey: string, overKey: string): string[] {
  const ord = fullColOrder(order);
  const from = ord.indexOf(dragKey), to = ord.indexOf(overKey);
  if (from < 0 || to < 0 || from === to) return ord;
  ord.splice(to, 0, ord.splice(from, 1)[0]);
  return ord;
}

export function visibleCols(hidden: Set<string>, order?: string[]): Col[] {
  const ord = order ?? loadColOrder();
  const vis = BASE_COLS.filter((c) => !hidden.has(c.key));
  if (!ord.length) return vis;
  const baseIdx = new Map(BASE_COLS.map((c, i) => [c.key, i]));
  const pos = (k: string) => {
    const i = ord.indexOf(k);
    return i === -1 ? 1000 + (baseIdx.get(k) ?? 0) : i;
  };
  return [...vis].sort((a, b) => pos(a.key) - pos(b.key));
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
  company_effect_rub: 140, adjusted_annual_effect: 120, adjusted_ebitda: 120, ebitda_per_story_point: 110,
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

// --- промежуточные итоги (личное, localStorage; несколько штук) ---
export type SubFn = "sum" | "avg" | "median" | "mode";
export interface Subtotal { id: string; col: string; fn: SubFn; }
const SUBTOTALS_KEY = "tetris_subtotals";
export function loadSubtotals(): Subtotal[] {
  try {
    const raw = localStorage.getItem(SUBTOTALS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}
export function saveSubtotals(s: Subtotal[]) {
  localStorage.setItem(SUBTOTALS_KEY, JSON.stringify(s));
}

// --- фильтры по оценённости (личное, localStorage) ---
// На каждую причину 2 независимых флага: show* (скрыть/показать строки) и warn* (значок ⚠).
export interface Filters {
  showUnderestimated: boolean; warnUnderestimated: boolean;
  showUnplatformed: boolean; warnUnplatformed: boolean;
  showEstimateNoTeam: boolean; warnEstimateNoTeam: boolean;
  showUnselectedEstimate: boolean; warnUnselectedEstimate: boolean;
}
const FILTERS_DEFAULT: Filters = {
  showUnderestimated: true, warnUnderestimated: true,
  showUnplatformed: true, warnUnplatformed: true,
  showEstimateNoTeam: true, warnEstimateNoTeam: true,
  showUnselectedEstimate: true, warnUnselectedEstimate: true,
};
const FILTERS_KEY = "tetris_filters";
export function loadFilters(): Filters {
  try {
    const raw = localStorage.getItem(FILTERS_KEY);
    if (raw) return { ...FILTERS_DEFAULT, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { ...FILTERS_DEFAULT };
}
export function saveFilters(f: Filters) {
  localStorage.setItem(FILTERS_KEY, JSON.stringify(f));
}

type WarnFlags = {
  is_underestimated: boolean;
  is_unplatformed: boolean;
  has_estimate_no_team: boolean;
  has_unselected_estimate: boolean;
};

/** Проходит ли задача фильтры по видимости строк (true = показывать). 4 непересекающихся признака. */
export function passFilters(t: WarnFlags, f: Filters): boolean {
  if (t.is_underestimated && !f.showUnderestimated) return false;
  if (t.is_unplatformed && !f.showUnplatformed) return false;
  if (t.has_estimate_no_team && !f.showEstimateNoTeam) return false;
  if (t.has_unselected_estimate && !f.showUnselectedEstimate) return false;
  return true;
}
/** Подпись для значка ⚠ — только по причинам, у которых включён показ ⚠ (пусто = значок не нужен). */
export function warnTitle(t: WarnFlags, f: Filters): string {
  const reasons: string[] = [];
  if (t.is_underestimated && f.warnUnderestimated) reasons.push("нет оценки у выбранной платформы");
  if (t.is_unplatformed && f.warnUnplatformed) reasons.push("без платформ и оценок");
  if (t.has_estimate_no_team && f.warnEstimateNoTeam) reasons.push("есть оценка, но команда не выбрана");
  if (t.has_unselected_estimate && f.warnUnselectedEstimate) reasons.push("есть оценка у невыбранной платформы");
  if (!reasons.length) return "";
  const s = reasons.join("; ");
  return s.charAt(0).toUpperCase() + s.slice(1);
}
/** Нужно ли показывать значок ⚠ для задачи. */
export function showWarn(t: WarnFlags, f: Filters): boolean {
  return warnTitle(t, f) !== "";
}

// --- фильтр по столбцам (личное, localStorage) ---
// hasValue — «только с значением» (>0 / непусто); min/max — для чисел; contains — для текста.
export interface ColFilter { hasValue?: boolean; min?: number | null; max?: number | null; contains?: string; }
const COLFILTERS_KEY = "tetris_colfilters";
export function loadColFilters(): Record<string, ColFilter> {
  try {
    const raw = localStorage.getItem(COLFILTERS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return {};
}
export function saveColFilters(f: Record<string, ColFilter>) {
  localStorage.setItem(COLFILTERS_KEY, JSON.stringify(f));
}
export function colFilterActive(f?: ColFilter): boolean {
  return !!(f && (f.hasValue || (f.contains && f.contains.length) || f.min != null || f.max != null));
}
/** Значение ячейки столбца для фильтрации (число для платформ/спринтов/числовых, иначе текст/число). */
export function colCellValue(
  colKey: string, task: Record<string, unknown>,
  platEst: Record<string, number>, platforms: { platform_id: number; sp_per_sprint: number }[],
): number | string | null {
  if (colKey.startsWith("plat_")) return platEst[colKey.slice(5)] ?? null;
  if (colKey.startsWith("spr_")) {
    const id = colKey.slice(4); const v = platEst[id];
    const sp = platforms.find((p) => String(p.platform_id) === id)?.sp_per_sprint;
    return v != null && sp ? v / sp : null;
  }
  const v = task[colKey];
  return (v as number | string | null) ?? null;
}
/** Проходит ли строка все активные фильтры столбцов. */
export function passColFilters(
  filters: Record<string, ColFilter>, task: Record<string, unknown>,
  platEst: Record<string, number>, platforms: { platform_id: number; sp_per_sprint: number }[],
): boolean {
  for (const [colKey, f] of Object.entries(filters)) {
    if (!colFilterActive(f)) continue;
    const val = colCellValue(colKey, task, platEst, platforms);
    if (f.hasValue) {
      const ok = typeof val === "number" ? val > 0 : val != null && val !== "" && val !== "—";
      if (!ok) return false;
    }
    if (f.contains && !String(val ?? "").toLowerCase().includes(f.contains.toLowerCase())) return false;
    if (f.min != null && !(typeof val === "number" && val >= f.min)) return false;
    if (f.max != null && !(typeof val === "number" && val <= f.max)) return false;
  }
  return true;
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


