import { useEffect, useState } from "react";
import { api } from "../api";
import type { GoalType, PlatformRef, TaskRanked } from "../types";
import { money } from "../format";

interface Props {
  task: TaskRanked;
  estimates: Record<string, number>;
  platforms: PlatformRef[];
  canEdit: boolean;
  onClose: () => void;
  onSaved: () => void;
  flash: (m: string) => void;
}

type Tab = "biz" | "tech" | "prio" | "done";

export function TaskModal({ task: t, estimates: est, platforms, canEdit, onClose, onSaved, flash }: Props) {
  const [goalTypes, setGoalTypes] = useState<GoalType[]>([]);
  const [tab, setTab] = useState<Tab>("biz");
  const [form, setForm] = useState({
    jira_key: t.jira_key,
    task_summary: t.task_summary ?? "",
    business_unit: t.business_unit ?? "",
    change_scope: t.change_scope ?? "",
    customer_name: t.customer_name ?? "",
    it_business_partner: t.it_business_partner ?? "",
    task_status: t.task_status ?? "",
    issue_type: t.issue_type ?? "",
    goal_type_name: t.goal_type_name ?? "",
    company_effect_rub: t.company_effect_rub ?? "",
    eta_months: t.eta_months ?? "",
    adjusted_ebitda: t.adjusted_ebitda ?? "",
    total_story_points: t.total_story_points ?? "",
    contractor_cost_rub: t.contractor_cost_rub ?? "",
    coefficient: t.coefficient ?? "",
    ceo_priority: t.ceo_priority ?? "",
    current_sprint: t.current_sprint ?? "",
    end_date: t.end_date ?? "",
    baseline_end_date: t.baseline_end_date ?? "",
    dod_text: t.dod_text ?? "",
    max_sprints_override: t.max_sprints_override ?? "",
  });
  const [estimates, setEstimates] = useState<Record<number, string>>(() => {
    const init: Record<number, string> = {};
    for (const p of platforms) { const v = est[String(p.platform_id)]; if (v) init[p.platform_id] = String(v); }
    return init;
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.goalTypes().then(setGoalTypes).catch(() => {}); }, []);

  const set = (k: keyof typeof form, v: string) => setForm({ ...form, [k]: v });
  const num = (v: string | number) => (v === "" || v === null ? null : Number(v));

  async function save() {
    setBusy(true);
    try {
      const goal = goalTypes.find((g) => g.goal_type_name === form.goal_type_name);
      await api.updateTask(t.task_id, {
        jira_key: form.jira_key || null,
        task_summary: form.task_summary || null,
        business_unit: form.business_unit || null,
        change_scope: form.change_scope || null,
        customer_name: form.customer_name || null,
        it_business_partner: form.it_business_partner || null,
        task_status: form.task_status || null,
        issue_type: form.issue_type || null,
        goal_type_id: goal ? goal.goal_type_id : null,
        company_effect_rub: num(form.company_effect_rub),
        eta_months: num(form.eta_months),
        adjusted_ebitda: num(form.adjusted_ebitda),
        total_story_points: num(form.total_story_points),
        contractor_cost_rub: num(form.contractor_cost_rub),
        coefficient: form.coefficient || null,
        ceo_priority: num(form.ceo_priority),
        current_sprint: form.current_sprint || null,
        end_date: form.end_date || null,
        baseline_end_date: form.baseline_end_date || null,
        dod_text: form.dod_text || null,
        max_sprints_override: num(form.max_sprints_override),
        platform_estimates: platforms
          .filter((p) => estimates[p.platform_id] !== undefined)
          .map((p) => ({ platform_id: p.platform_id, estimate_story_points: num(estimates[p.platform_id] ?? "") })),
      });
      flash("Сохранено в базу");
      onSaved();
      onClose();
    } catch (e) {
      flash(e instanceof Error ? e.message : "Ошибка");
    } finally { setBusy(false); }
  }

  async function sync() {
    setBusy(true);
    try { await api.syncTask(t.task_id); flash("Синхронизация записана в журнал (заглушка — Jira на этапе 12)"); }
    catch (e) { flash(e instanceof Error ? e.message : "Ошибка"); }
    finally { setBusy(false); }
  }

  // одно поле Jira-стиля (label сверху, поле снизу)
  const field = (label: string, key: keyof typeof form, type = "text", hint?: string) => (
    <label className="jff">
      <span className="jff-label">{label}</span>
      <input type={type} value={form[key] as string} disabled={!canEdit} onChange={(e) => set(key, e.target.value)} />
      {hint && <span className="jff-hint">{hint}</span>}
    </label>
  );
  const area = (label: string, key: keyof typeof form, rows = 3) => (
    <label className="jff">
      <span className="jff-label">{label}</span>
      <textarea rows={rows} value={form[key] as string} disabled={!canEdit} onChange={(e) => set(key, e.target.value)} />
    </label>
  );
  const ro = (label: string, value: string) => (
    <div className="jff">
      <span className="jff-label">{label}</span>
      <div className="jff-ro">{value}</div>
    </div>
  );

  const tabs: { id: Tab; label: string }[] = [
    { id: "biz", label: "Бизнес-информация" },
    { id: "tech", label: "Техническая информация" },
    { id: "prio", label: "Приоритизация" },
    { id: "done", label: "Подтверждение результата" },
  ];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal--jira" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-title">
            Редактирование задачи :{" "}
            <a className="jira-key" href={`https://jira.askona.ru/browse/${t.jira_key}`} target="_blank" rel="noreferrer">{t.jira_key} ↗</a>
            {t.is_underestimated && <span className="chip warn">⚠ нет оценки</span>}
          </div>
          <button className="x" onClick={onClose}>✕</button>
        </div>

        <div className="jira-tabs">
          {tabs.map((tb) => (
            <button key={tb.id} className={`jira-tab${tab === tb.id ? " active" : ""}`} onClick={() => setTab(tb.id)}>{tb.label}</button>
          ))}
        </div>

        <div className="jira-form">
          {tab === "biz" && (
            <>
              {field("Тип задачи", "issue_type")}
              {field("Business unit", "business_unit")}
              <label className="jff">
                <span className="jff-label">Тип цели</span>
                <select value={form.goal_type_name} disabled={!canEdit} onChange={(e) => set("goal_type_name", e.target.value)}>
                  <option value="">—</option>
                  {goalTypes.map((g) => <option key={g.goal_type_id} value={g.goal_type_name}>{g.goal_type_name}</option>)}
                </select>
              </label>
              {field("Заказчик", "customer_name")}
              {field("IT Бизнес-партнёр", "it_business_partner")}
              {area("Тема", "task_summary", 2)}
              {area("Change scope (что меняем)", "change_scope", 2)}
              {area("DoD (Definition of Done)", "dod_text", 4)}
            </>
          )}

          {tab === "tech" && (
            <>
              {ro("Платформы (нужны)", t.platforms_required ?? "—")}
              {field("Story Points (итого)", "total_story_points", "number")}
              {field("МАКСИМУМ спринтов", "max_sprints_override", "number", "0 или пусто — считается автоматически по оценкам платформ")}
              <div className="jff-section">Оценки по платформам (SP)</div>
              <div className="jira-plat-grid">
                {platforms.map((p) => (
                  <label key={p.platform_id} className="jff jff--inline">
                    <span className="jff-label">Оценка {p.platform_name}</span>
                    <input type="number" value={estimates[p.platform_id] ?? ""} disabled={!canEdit}
                           onChange={(e) => setEstimates({ ...estimates, [p.platform_id]: e.target.value })} />
                  </label>
                ))}
              </div>
            </>
          )}

          {tab === "prio" && (
            <>
              {field("Коэффициент", "coefficient")}
              {field("Приоритет CEO", "ceo_priority", "number")}
              {field("Эффект для компании, ₽", "company_effect_rub", "number")}
              {field("ETA, мес", "eta_months", "number")}
              {field("Приведённая EBITDA, ₽", "adjusted_ebitda", "number")}
              {field("Подрядчики, ₽", "contractor_cost_rub", "number")}
              {field("End date", "end_date", "date")}
              {field("Baseline end date", "baseline_end_date", "date")}
              {field("Текущий спринт", "current_sprint")}
            </>
          )}

          {tab === "done" && (
            <>
              {ro("Приведённый годовой эффект", money(t.adjusted_annual_effect))}
              {ro("Приведённая EBITDA", money(t.adjusted_ebitda))}
              {ro("EBITDA на Story Point (считается)", money(t.ebitda_per_story_point))}
              {ro("МАКСИМУМ спринтов (итог)", (t.max_sprints ?? "—").toString())}
              {ro("Метки", t.labels ?? "—")}
            </>
          )}
        </div>

        <div className="modal-foot">
          {canEdit && <button onClick={sync} disabled={busy} title="Отправить изменения в Jira (заглушка)">⟳ Синхронизировать с Jira</button>}
          <span className="spacer" />
          {!canEdit && <span className="lock-note">🔒 только просмотр</span>}
          <button onClick={onClose}>Отменить</button>
          {canEdit && <button className="primary" onClick={save} disabled={busy}>Обновить</button>}
        </div>
      </div>
    </div>
  );
}
