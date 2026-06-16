import { useEffect, useMemo, useRef, useState } from "react";
import { api, hasToken, setToken } from "./api";
import type { AutoData, Grid as GridData, Plan, Presentation, Quarter, TaskRanked, User } from "./types";
import { Login } from "./components/Login";
import { Grid } from "./components/Grid";
import { Autovygruzka } from "./components/Autovygruzka";
import { TaskModal } from "./components/TaskModal";
import { ColumnsMenu } from "./components/ColumnsMenu";
import { VelocityModal } from "./components/VelocityModal";
import { DEFAULT_HIDDEN } from "./components/columns";

type View = "auto" | "plan";
const HIDDEN_KEY = "tetris_hidden_cols";

function loadHidden(): Set<string> {
  try {
    const raw = localStorage.getItem(HIDDEN_KEY);
    if (raw) return new Set(JSON.parse(raw));
  } catch { /* ignore */ }
  return new Set(DEFAULT_HIDDEN);
}

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);

  const [metasprints, setMetasprints] = useState<Quarter[]>([]);
  const [metasprintId, setMetasprintId] = useState<number | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [planId, setPlanId] = useState<number | null>(null);
  const [view, setView] = useState<View>("auto");

  const [auto, setAuto] = useState<AutoData | null>(null);
  const [grid, setGrid] = useState<GridData | null>(null);
  const [present, setPresent] = useState<Presentation>({});

  const [search, setSearch] = useState("");
  const [hidden, setHidden] = useState<Set<string>>(loadHidden);
  const [openTask, setOpenTask] = useState<{ task: TaskRanked; est: Record<string, number> } | null>(null);
  const [renaming, setRenaming] = useState<{ type: "plan" | "ms"; id: number } | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [velocityOpen, setVelocityOpen] = useState(false);
  const saveTimer = useRef<number | null>(null);

  const canEdit = user?.user_role === "editor";
  const currentPlan = plans.find((p) => p.plan_id === planId) ?? null;
  const canEditPlan = canEdit && currentPlan?.plan_status === "draft";

  function pickDefaultPlan(ps: Plan[]): number | null {
    if (!ps.length) return null;
    const approved = ps.find((p) => p.plan_status === "approved");
    if (approved) return approved.plan_id;
    const drafts = ps.filter((p) => p.plan_status === "draft");
    const pool = drafts.length ? drafts : ps;
    const latest = [...pool].sort((a, b) =>
      (b.updated_at ?? b.created_at).localeCompare(a.updated_at ?? a.created_at))[0];
    return latest.plan_id;
  }

  function changeHidden(h: Set<string>) {
    setHidden(h);
    localStorage.setItem(HIDDEN_KEY, JSON.stringify([...h]));
  }

  useEffect(() => {
    if (!hasToken()) return setBooting(false);
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setBooting(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    api.quarters().then((qs) => { setMetasprints(qs); if (qs.length) setMetasprintId(qs[0].quarter_id); });
  }, [user]);

  useEffect(() => {
    if (metasprintId === null) return;
    api.plans(metasprintId).then((ps) => {
      setPlans(ps);
      const def = pickDefaultPlan(ps);
      setPlanId(def);
      setView(def ? "plan" : "auto");
    });
  }, [metasprintId]);

  function reloadAuto() { api.autovygruzka(planId ?? undefined).then(setAuto); }
  function reloadGrid() {
    if (planId === null) { setGrid(null); return; }
    api.grid(planId).then((g) => { setGrid(g); setPresent(g.presentation ?? {}); });
  }
  useEffect(() => { view === "auto" ? reloadAuto() : reloadGrid(); }, [view, planId]);

  function changePresentation(p: Presentation) {
    setPresent(p);
    if (planId === null) return;
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(() => { api.savePresentation(planId, p).catch(() => {}); }, 600);
  }

  async function addToPlan(taskId: number) {
    if (planId === null) return flash("Сначала выберите план снизу");
    await api.addTaskToPlan(planId, taskId);
    reloadAuto();
    flash(`Добавлено в ${currentPlan?.plan_name}`);
  }
  async function removeFromPlan(taskId: number) {
    if (planId === null) return;
    await api.removeTaskFromPlan(planId, taskId);
    reloadGrid();
  }

  async function changeStatus(value: string) {
    if (planId === null) return;
    await api.setStatus(planId, value);
    setPlans(await api.plans(metasprintId ?? undefined));
    flash(`Статус плана: ${value === "draft" ? "черновик" : value === "approved" ? "утверждён" : "архив"}`);
  }
  async function newPlan() {
    if (metasprintId === null) return flash("Сначала создайте метаспринт");
    const plan = await api.createPlan({ quarter_id: metasprintId });
    setPlans(await api.plans(metasprintId));
    setPlanId(plan.plan_id);
    setView("plan");
    flash(`Создан ${plan.plan_name}`);
  }
  async function deletePlan() {
    if (planId === null || !currentPlan) return;
    if (!window.confirm(`Удалить «${currentPlan.plan_name}»? Действие необратимо.`)) return;
    await api.deletePlan(planId);
    const ps = await api.plans(metasprintId ?? undefined);
    setPlans(ps);
    setPlanId(ps.length ? ps[0].plan_id : null);
    setView(ps.length ? "plan" : "auto");
    flash("План удалён");
  }
  async function newMetasprint() {
    const name = prompt("Название метаспринта", `Метаспринт ${metasprints.length + 1}`);
    if (!name) return;
    const q = await api.createQuarter({ quarter_name: name, quarter_year: 2026, quarter_number: (metasprints.length % 4) + 1 });
    setMetasprints(await api.quarters());
    setMetasprintId(q.quarter_id);
    flash(`Метаспринт «${name}» создан`);
  }
  async function deleteMetasprint() {
    if (metasprintId === null) return;
    const m = metasprints.find((x) => x.quarter_id === metasprintId);
    if (!window.confirm(`Удалить метаспринт «${m?.quarter_name}» со всеми его планами? Необратимо.`)) return;
    await api.deleteMetasprint(metasprintId);
    const qs = await api.quarters();
    setMetasprints(qs);
    setMetasprintId(qs.length ? qs[0].quarter_id : null);
    flash("Метаспринт удалён");
  }
  async function commitRename(value: string) {
    const r = renaming;
    setRenaming(null);
    const name = value.trim();
    if (!r || !name) return;
    if (r.type === "plan") { await api.renamePlan(r.id, name); setPlans(await api.plans(metasprintId ?? undefined)); }
    else { await api.renameMetasprint(r.id, name); setMetasprints(await api.quarters()); }
    flash("Переименовано");
  }
  async function reloadFromJira() {
    await api.reloadFromFile();
    view === "auto" ? reloadAuto() : reloadGrid();
    flash("Задачи перечитаны из выгрузки");
  }

  function flash(m: string) { setStatus(m); setTimeout(() => setStatus(null), 2600); }
  function logout() { setToken(null); setUser(null); setGrid(null); setAuto(null); setPlans([]); }

  const filteredGridRows = useMemo(() => {
    if (!grid) return [];
    const q = search.trim().toLowerCase();
    return grid.rows.filter((r) => !q || `${r.task.jira_key} ${r.task.task_summary ?? ""}`.toLowerCase().includes(q));
  }, [grid, search]);

  const STATUS_RU: Record<string, string> = { draft: "черновик", approved: "утверждён", archived: "архив" };

  if (booting) return <div className="center muted">Загрузка…</div>;
  if (!user) return <Login onLogin={setUser} />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">Тетрис</div>
        <input className="search" placeholder="Поиск Key / Summary…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <ColumnsMenu hidden={hidden} onChange={changeHidden} />
        {canEdit && <button className="hb" onClick={() => setVelocityOpen(true)} title="Velocity платформ (SP в спринт)">⚙ SP/спринт</button>}
        {canEdit && <button className="hb" onClick={reloadFromJira} title="Перечитать выгрузку">⟳ из Jira</button>}
        <div className="user">
          <span className="user-email" title="Вы вошли как">✉ {user.user_email}</span>
          <span className="role-badge">{user.user_role === "editor" ? "редактор" : "читатель"}</span>
          <button onClick={logout}>Выйти</button>
        </div>
      </header>

      {status && <div className="toast">{status}</div>}

      {view === "auto" ? (
        auto ? (
          <Autovygruzka data={auto} search={search} hidden={hidden} canEdit={canEdit}
                        targetPlan={currentPlan} onAdd={addToPlan}
                        onOpen={(t) => setOpenTask({ task: t, est: (auto.rows.find((r) => r.task.task_id === t.task_id)?.platform_estimates) ?? {} })} />
        ) : <div className="center muted">Загрузка…</div>
      ) : grid ? (
        <Grid grid={grid} rows={filteredGridRows} canEdit={canEditPlan} hidden={hidden}
              presentation={present} onPresentation={changePresentation} onRemove={removeFromPlan}
              onOpen={(t) => setOpenTask({ task: t, est: (grid.rows.find((r) => r.task.task_id === t.task_id)?.platform_estimates) ?? {} })} />
      ) : (
        <div className="center muted">{plans.length === 0 ? "В этом метаспринте нет планов. Создайте план снизу." : "Выберите план"}</div>
      )}

      <footer className="bottom">
        {/* ряд 1: автовыгрузка + метаспринты */}
        <div className="ms-row">
          <button className={`tab tab-auto${view === "auto" ? " tab-active" : ""}`} onClick={() => setView("auto")}>📥 Автовыгрузка</button>
          <span className="tab-sep" />
          <span className="row-label">Метаспринты:</span>
          {metasprints.map((m) => (
            renaming?.type === "ms" && renaming.id === m.quarter_id ? (
              <input key={m.quarter_id} className="tab tab-rename" defaultValue={m.quarter_name} autoFocus
                     onKeyDown={(e) => { if (e.key === "Enter") commitRename(e.currentTarget.value); if (e.key === "Escape") setRenaming(null); }}
                     onBlur={(e) => commitRename(e.currentTarget.value)} />
            ) : (
              <button key={m.quarter_id} className={`tab${m.quarter_id === metasprintId ? " tab-active" : ""}`}
                      title="двойной клик — переименовать"
                      onClick={() => { setMetasprintId(m.quarter_id); setView("auto"); }}
                      onDoubleClick={() => setRenaming({ type: "ms", id: m.quarter_id })}>{m.quarter_name}</button>
            )
          ))}
          {canEdit && <button className="tab tab-add" onClick={newMetasprint}>+ метаспринт</button>}
          <span className="spacer" />
          {canEdit && metasprintId !== null && (
            <button className="tab tab-del" onClick={deleteMetasprint} title="Удалить метаспринт (со всеми планами)">🗑 удалить метаспринт</button>
          )}
        </div>
        {/* ряд 2: планы выбранного метаспринта со статусом */}
        <div className="plan-row">
          <span className="row-label">Планы:</span>
          {plans.length === 0 && <span className="muted">нет планов</span>}
          {plans.map((p) => (
            renaming?.type === "plan" && renaming.id === p.plan_id ? (
              <input key={p.plan_id} className="tab tab-rename" defaultValue={p.plan_name} autoFocus
                     onKeyDown={(e) => { if (e.key === "Enter") commitRename(e.currentTarget.value); if (e.key === "Escape") setRenaming(null); }}
                     onBlur={(e) => commitRename(e.currentTarget.value)} />
            ) : (
              <button key={p.plan_id}
                      className={`tab plan-tab${view === "plan" && p.plan_id === planId ? " tab-active" : ""}${p.plan_status === "approved" ? " tab-approved" : ""}`}
                      title="двойной клик — переименовать"
                      onClick={() => { setPlanId(p.plan_id); setView("plan"); }}
                      onDoubleClick={() => setRenaming({ type: "plan", id: p.plan_id })}>
                {p.plan_name}<span className={`st st-${p.plan_status}`}>{STATUS_RU[p.plan_status] ?? p.plan_status}</span>
              </button>
            )
          ))}
          {canEdit && <button className="tab tab-add" onClick={newPlan}>+ план</button>}
          <span className="spacer" />
          {canEdit && currentPlan && (
            <span className="status-pick">
              статус:
              <select value={currentPlan.plan_status} onChange={(e) => changeStatus(e.target.value)}>
                <option value="draft">черновик</option>
                <option value="approved">утверждён</option>
                <option value="archived">архив</option>
              </select>
            </span>
          )}
          {canEdit && currentPlan && (
            <button className="tab tab-del" onClick={deletePlan} title="Удалить план">🗑 удалить</button>
          )}
        </div>
      </footer>

      {openTask && (
        <TaskModal task={openTask.task} estimates={openTask.est}
                   platforms={(grid?.platforms ?? auto?.platforms) ?? []}
                   canEdit={view === "plan" ? canEditPlan : canEdit}
                   onClose={() => setOpenTask(null)}
                   onSaved={() => { view === "auto" ? reloadAuto() : reloadGrid(); }} flash={flash} />
      )}
      {velocityOpen && (
        <VelocityModal onClose={() => setVelocityOpen(false)}
                       onSaved={() => { view === "auto" ? reloadAuto() : reloadGrid(); }} flash={flash} />
      )}
    </div>
  );
}
