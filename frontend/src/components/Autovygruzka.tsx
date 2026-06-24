import { useEffect, useMemo, useState } from "react";
import type { AutoData, AutoRow, Plan } from "../types";
import {
  visibleCols, platformsVisible, sprintsVisible, colWidth, loadWidths, saveWidths,
  passFilters, warnTitle, showWarn,
  loadColFilters, saveColFilters, passColFilters, colFilterActive,
  loadColOrder, saveColOrder, reorderCols,
  type Filters, type ColFilter,
} from "./columns";
import { ColumnFilter } from "./ColumnFilter";
import { money } from "../format";

interface Props {
  data: AutoData;
  search: string;
  hidden: Set<string>;
  filters: Filters;
  canEdit: boolean;
  targetPlan: Plan | null;
  onAdd: (taskId: number) => void;
  onOpen: (task: AutoRow["task"]) => void;
}

const ZONE_ORDER = ["MetaSprint", "AlphaSprint", "OpenSprint", "To be allocated"];
const zoneRank = (z: string) => { const i = ZONE_ORDER.indexOf(z); return i === -1 ? 999 : i; };

export function Autovygruzka({ data, search, hidden, filters, canEdit, targetPlan, onAdd, onOpen }: Props) {
  const [colOrder, setColOrder] = useState<string[]>(loadColOrder);
  const [dragCol, setDragCol] = useState<string | null>(null);
  const cols = visibleCols(hidden, colOrder);
  const showPlat = platformsVisible(hidden);
  const showSprints = sprintsVisible(hidden);
  const [sortKey, setSortKey] = useState<string>("adjusted_ebitda");
  const [asc, setAsc] = useState(false);
  const [widths, setWidths] = useState<Record<string, number>>(loadWidths);
  const [selId, setSelId] = useState<number | null>(null);  // выделенная строка (для удобной прокрутки)
  const [colFilters, setColFilters] = useState<Record<string, ColFilter>>(loadColFilters);
  useEffect(() => { saveWidths(widths); }, [widths]);
  function onColDrop(overKey: string) {
    if (!dragCol || dragCol === overKey) { setDragCol(null); return; }
    const next = reorderCols(colOrder, dragCol, overKey);
    setColOrder(next); saveColOrder(next); setDragCol(null);
  }
  useEffect(() => { saveColFilters(colFilters); }, [colFilters]);
  function setColFilter(key: string, f: ColFilter | undefined) {
    setColFilters((prev) => { const n = { ...prev }; if (f) n[key] = f; else delete n[key]; return n; });
  }
  const anyColFilter = Object.values(colFilters).some(colFilterActive);

  function toggleSort(k: string) { if (k === sortKey) setAsc(!asc); else { setSortKey(k); setAsc(false); } }
  const arrow = (k: string) => (k === sortKey ? (asc ? " ▲" : " ▼") : "");

  function startResize(e: React.MouseEvent, key: string) {
    e.preventDefault(); e.stopPropagation();
    const startX = e.clientX, startW = colWidth(widths, key);
    const move = (ev: MouseEvent) => setWidths((w) => ({ ...w, [key]: Math.max(36, startW + ev.clientX - startX) }));
    const up = () => { document.removeEventListener("mousemove", move); document.removeEventListener("mouseup", up); };
    document.addEventListener("mousemove", move); document.addEventListener("mouseup", up);
  }

  const groups = useMemo(() => {
    const q = search.trim().toLowerCase();
    const filtered = data.rows.filter((r) =>
      passFilters(r.task, filters) &&
      passColFilters(colFilters, r.task as unknown as Record<string, unknown>, r.platform_estimates, data.platforms) &&
      (!q || `${r.task.jira_key} ${r.task.task_summary ?? ""}`.toLowerCase().includes(q)));
    const byZone = new Map<string, AutoRow[]>();
    for (const r of filtered) { if (!byZone.has(r.zone_name)) byZone.set(r.zone_name, []); byZone.get(r.zone_name)!.push(r); }
    const sortRows = (rs: AutoRow[]) => [...rs].sort((a, b) => {
      const va = (a.task as any)[sortKey] ?? "", vb = (b.task as any)[sortKey] ?? "";
      const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), "ru");
      return asc ? cmp : -cmp;
    });
    return [...byZone.keys()].sort((a, b) => zoneRank(a) - zoneRank(b)).map((n) => ({ zone: n, rows: sortRows(byZone.get(n)!) }));
  }, [data.rows, data.platforms, search, filters, colFilters, sortKey, asc]);

  const wKey = colWidth(widths, "__key");
  const colspan = 2 + cols.length + (showPlat ? data.platforms.length : 0) + (showSprints ? data.platforms.length : 0);
  const sumSP = (rs: AutoRow[]) => rs.reduce((s, r) => s + (Number(r.task.total_story_points) || 0), 0);
  const sumEb = (rs: AutoRow[]) => rs.reduce((s, r) => s + (Number(r.task.adjusted_ebitda) || 0), 0);

  return (
    <div className="grid-wrap">
      <div className="grid-subtoolbar">
        <span className="auto-badge">Автовыгрузка · группировка по колодцам</span>
        {anyColFilter && <button className="mini" onClick={() => setColFilters({})} title="Сбросить фильтры по столбцам">✕ фильтры столбцов</button>}
        <span className="spacer" />
        {canEdit && (
          <span className={`target-plan ${targetPlan ? "" : "no-target"}`}>
            {targetPlan ? `+ добавляю в: ${targetPlan.plan_name}` : "выберите план снизу, чтобы добавлять"}
          </span>
        )}
      </div>
      <div className="grid-scroll">
        <table className="grid grid--frozen grid--fixed">
          <colgroup>
            <col style={{ width: wKey }} />
            <col style={{ width: colWidth(widths, "__summary") }} />
            {cols.map((c) => <col key={c.key} style={{ width: colWidth(widths, c.key) }} />)}
            {showPlat && data.platforms.map((p) => <col key={p.platform_id} style={{ width: colWidth(widths, "__plat") }} />)}
            {showSprints && data.platforms.map((p) => <col key={`s${p.platform_id}`} style={{ width: colWidth(widths, "__sprint") }} />)}
          </colgroup>
          <thead>
            <tr>
              <th className="col-key">
                <span className="sortable" onClick={() => toggleSort("jira_key")}>Key{arrow("jira_key")}</span>
                <span className="rsz" onMouseDown={(e) => startResize(e, "__key")} />
              </th>
              <th className="col-summary">Summary
                <span className="rsz" onMouseDown={(e) => startResize(e, "__summary")} />
              </th>
              {cols.map((c) => (
                <th key={c.key} className={`${c.num ? "num" : ""}${dragCol === c.key ? " col-dragging" : ""}`}
                    onDragOver={(e) => { if (dragCol) e.preventDefault(); }} onDrop={() => onColDrop(c.key)}>
                  <span className="col-drag" draggable title="перетащить столбец"
                        onDragStart={() => setDragCol(c.key)} onDragEnd={() => setDragCol(null)}>⠿</span>
                  <span className="sortable" onClick={() => toggleSort(c.key)}>{c.label}{arrow(c.key)}</span>
                  <ColumnFilter colKey={c.key} numeric={!!c.num} filter={colFilters[c.key]} onChange={(f) => setColFilter(c.key, f)} />
                  <span className="rsz" onMouseDown={(e) => startResize(e, c.key)} />
                </th>
              ))}
              {showPlat && data.platforms.map((p, i) => (
                <th key={p.platform_id} className="col-plat" title={p.platform_name}>{p.platform_name}
                  <ColumnFilter colKey={`plat_${p.platform_id}`} numeric filter={colFilters[`plat_${p.platform_id}`]} onChange={(f) => setColFilter(`plat_${p.platform_id}`, f)} />
                  {i === 0 && <span className="rsz" onMouseDown={(e) => startResize(e, "__plat")} />}
                </th>
              ))}
              {showSprints && data.platforms.map((p, i) => (
                <th key={`s${p.platform_id}`} className="col-plat col-sprint" title={`спринты по «${p.platform_name}» (velocity ${p.sp_per_sprint} SP/спринт)`}>сп: {p.platform_name}
                  <ColumnFilter colKey={`spr_${p.platform_id}`} numeric filter={colFilters[`spr_${p.platform_id}`]} onChange={(f) => setColFilter(`spr_${p.platform_id}`, f)} />
                  {i === 0 && <span className="rsz" onMouseDown={(e) => startResize(e, "__sprint")} />}
                </th>
              ))}
            </tr>
          </thead>
          {groups.map((g) => (
            <tbody key={g.zone}>
              <tr className="group-head">
                <td colSpan={colspan}>
                  <span className="group-name">{g.zone}</span>
                  <span className="group-stat">задач: {g.rows.length}</span>
                  <span className="group-stat">Σ SP: {sumSP(g.rows)}</span>
                  <span className="group-stat">Σ EBITDA: {money(sumEb(g.rows))}</span>
                </td>
              </tr>
              {g.rows.map((r) => {
                const t = r.task;
                return (
                  <tr key={t.task_id} className={`${r.in_plan ? "row-committed" : ""}${selId === t.task_id ? " row-selected" : ""}`}
                      onClick={() => setSelId(selId === t.task_id ? null : t.task_id)}
                      onDoubleClick={() => onOpen(t)}>
                    <td className="col-key">
                      {canEdit && (
                        <button className="pm plus" disabled={!targetPlan || r.in_plan}
                                title={r.in_plan ? "Уже в плане" : "Добавить в выбранный план"}
                                onClick={(e) => { e.stopPropagation(); onAdd(t.task_id); }}>{r.in_plan ? "✓" : "+"}</button>
                      )}
                      <span className="jira-key">{t.jira_key}</span>
                      {showWarn(t, filters) && <span className="warn" title={warnTitle(t, filters)}>⚠</span>}
                    </td>
                    <td className="col-summary" title={t.task_summary ?? ""}>{t.task_summary ?? "—"}</td>
                    {cols.map((c) => <td key={c.key} className={c.num ? "num" : ""}>{c.cell(t)}</td>)}
                    {showPlat && data.platforms.map((p) => {
                      const v = r.platform_estimates[String(p.platform_id)];
                      return <td key={p.platform_id} className={`num col-plat${v ? " plat-filled" : ""}`}>{v ?? ""}</td>;
                    })}
                    {showSprints && data.platforms.map((p) => {
                      const v = r.platform_estimates[String(p.platform_id)];
                      const sprints = v != null && p.sp_per_sprint ? v / p.sp_per_sprint : null;
                      return <td key={`s${p.platform_id}`} className={`num col-plat col-sprint${sprints ? " plat-filled" : ""}`}>{sprints ? sprints.toFixed(1) : ""}</td>;
                    })}
                  </tr>
                );
              })}
            </tbody>
          ))}
        </table>
      </div>
    </div>
  );
}
