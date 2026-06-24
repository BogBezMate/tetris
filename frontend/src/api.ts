import type {
  AutoData,
  Board,
  GoalType,
  Grid,
  Plan,
  Presentation,
  PlatformRef,
  Quarter,
  QuarterVelocity,
  TaskRanked,
  User,
  Zone,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

let token: string | null = localStorage.getItem("tetris_token");

export function setToken(value: string | null) {
  token = value;
  if (value) localStorage.setItem("tetris_token", value);
  else localStorage.removeItem("tetris_token");
}

export function hasToken(): boolean {
  return Boolean(token);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${BASE}${path}`, { ...options, headers });
  if (resp.status === 401) {
    setToken(null);
    throw new Error("Сессия истекла, войдите снова");
  }
  if (!resp.ok) {
    const detail = await resp.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Ошибка ${resp.status}`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>("/api/auth/me"),
  tasks: () => request<TaskRanked[]>("/api/tasks"),
  zones: () => request<Zone[]>("/api/zones"),
  quarters: () => request<Quarter[]>("/api/quarters"),
  createQuarter: (body: {
    quarter_name: string;
    quarter_year: number;
    quarter_number: number;
  }) =>
    request<Quarter>("/api/quarters", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  plans: (quarterId?: number) =>
    request<Plan[]>(`/api/plans${quarterId ? `?quarter_id=${quarterId}` : ""}`),
  createPlan: (body: { quarter_id: number; plan_name?: string }) =>
    request<Plan>("/api/plans", { method: "POST", body: JSON.stringify(body) }),
  duplicatePlan: (planId: number) =>
    request<Plan>(`/api/plans/${planId}/duplicate`, { method: "POST" }),
  board: (planId: number) => request<Board>(`/api/plans/${planId}/board`),
  grid: (planId: number) => request<Grid>(`/api/plans/${planId}/grid`),
  autovygruzka: (planId?: number) =>
    request<AutoData>(`/api/autovygruzka${planId ? `?plan_id=${planId}` : ""}`),
  addTaskToPlan: (planId: number, taskId: number) =>
    request<{ ok: boolean }>(`/api/plans/${planId}/items`, {
      method: "POST",
      body: JSON.stringify({ task_id: taskId }),
    }),
  removeTaskFromPlan: (planId: number, taskId: number) =>
    request<{ ok: boolean }>(`/api/plans/${planId}/items/${taskId}`, { method: "DELETE" }),
  savePresentation: (planId: number, data: Presentation) =>
    request<{ ok: boolean }>(`/api/plans/${planId}/presentation`, {
      method: "PUT",
      body: JSON.stringify({ data }),
    }),
  approvePlan: (planId: number) =>
    request<Plan>(`/api/plans/${planId}/approve`, { method: "POST" }),
  setStatus: (planId: number, value: string) =>
    request<Plan>(`/api/plans/${planId}/status?value=${value}`, { method: "PUT" }),
  reorderPlan: (planId: number, taskIds: number[]) =>
    request<{ ok: boolean }>(`/api/plans/${planId}/reorder`, {
      method: "PUT",
      body: JSON.stringify({ task_ids: taskIds }),
    }),
  goalTypes: () => request<GoalType[]>("/api/goal-types"),
  platforms: () => request<PlatformRef[]>("/api/platforms"),
  saveVelocity: (items: { platform_id: number; sp_per_sprint: number }[]) =>
    request<PlatformRef[]>("/api/platforms/velocity", {
      method: "PUT",
      body: JSON.stringify(items),
    }),
  quarterVelocity: (quarterId: number) =>
    request<QuarterVelocity[]>(`/api/quarters/${quarterId}/velocity`),
  saveQuarterVelocity: (quarterId: number, items: { platform_id: number; capacity_sp: number | null; sp_per_sprint: number | null }[]) =>
    request<QuarterVelocity[]>(`/api/quarters/${quarterId}/velocity`, {
      method: "PUT",
      body: JSON.stringify(items),
    }),
  savePlanEstimates: (planId: number, taskId: number, items: { platform_id: number; estimate_sp: number | null }[]) =>
    request<{ ok: boolean }>(`/api/plans/${planId}/tasks/${taskId}/estimates`, {
      method: "PUT",
      body: JSON.stringify({ items }),
    }),
  deletePlan: (planId: number) =>
    request<{ ok: boolean }>(`/api/plans/${planId}`, { method: "DELETE" }),
  renamePlan: (planId: number, name: string) =>
    request<Plan>(`/api/plans/${planId}/rename?name=${encodeURIComponent(name)}`, { method: "PUT" }),
  renameMetasprint: (quarterId: number, name: string) =>
    request<Quarter>(`/api/quarters/${quarterId}/rename?name=${encodeURIComponent(name)}`, { method: "PUT" }),
  deleteMetasprint: (quarterId: number) =>
    request<{ ok: boolean }>(`/api/quarters/${quarterId}`, { method: "DELETE" }),
  updateTask: (taskId: number, body: Record<string, unknown>) =>
    request<TaskRanked>(`/api/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  syncTask: (taskId: number) =>
    request<{ ok: boolean; stub: boolean; jira_key: string }>(
      `/api/tasks/${taskId}/sync-jira`,
      { method: "POST" }
    ),
  reloadFromFile: () =>
    request<{ loaded: number; failed: number; total: number }>(
      "/api/tasks/reload-from-file",
      { method: "POST" }
    ),
};
