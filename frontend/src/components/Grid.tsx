import { Fragment, useEffect, useRef, useState } from "react";
import type { Grid as GridData, GridRow, Note, Presentation, TaskRanked } from "../types";
import {
  visibleCols, platformsVisible, sprintsVisible, colWidth, loadWidths, saveWidths,
  loadPalette, savePalette, loadColOrder, saveColOrder, reorderCols,
  loadSubtotals, saveSubtotals, warnTitle, showWarn,
  loadColFilters, saveColFilters, passColFilters, colFilterActive,
  type Col, type Subtotal, type SubFn, type Filters, type ColFilter,
} from "./columns";
import { ColumnFilter } from "./ColumnFilter";
import { money, numFmt } from "../format";
import { NoteModal } from "./NoteModal";

interface Props {
  grid: GridData;
  rows: GridRow[];
  canEdit: boolean;
  hidden: Set<string>;
  filters: Filters;
  presentation: Presentation;
  onPresentation: (p: Presentation) => void;
  onRemove: (taskId: number) => void;
  onOpen: (task: TaskRanked) => void;
}

interface CheckCfg { on: boolean; column: string; color: string; }
type Item = { type: "task"; row: GridRow } | { type: "note"; note: Note };

export function Grid({ grid, rows, canEdit, hidden, filters, presentation, onPresentation, onRemove, onOpen }: Props) {
  const [colOrder, setColOrder] = useState<string[]>(loadColOrder);
  const [dragCol, setDragCol] = useState<string | null>(null);
  const cols = visibleCols(hidden, colOrder);
  const showPlat = platformsVisible(hidden);
  const showSprints = sprintsVisible(hidden);

  const [widths, setWidths] = useState<Record<string, number>>(loadWidths);
  const [palette, setPalette] = useState<string[]>(loadPalette);
  const [sortKey, setSortKey] = useState<string>("");
  const [asc, setAsc] = useState(false);
  const [dragOrder, setDragOrder] = useState<string[] | null>(null);
  const [dragTok, setDragTok] = useState<string | null>(null);
  const [selId, setSelId] = useState<number | null>(null);  // выделенная строка (для удобной прокрутки)
  const [colFilters, setColFilters] = useState<Record<string, ColFilter>>(loadColFilters);
  useEffect(() => { saveColFilters(colFilters); }, [colFilters]);
  function setColFilter(key: string, f: ColFilter | undefined) {
    setColFilters((prev) => { const n = { ...prev }; if (f) n[key] = f; else delete n[key]; return n; });
  }
  const anyColFilter = Object.values(colFilters).some(colFilterActive);

  const [brushOn, setBrushOn] = useState(false);
  const [brushColor, setBrushColor] = useState<string>("");
  const [editingNote, setEditingNote] = useState<string | null>(null);
  const painting = useRef(false);
  // отмена правок кисти, пока кисть активна
  const undoStack = useRef<Presentation[]>([]);
  const brushBaseline = useRef<Presentation | null>(null);
  const presRef = useRef<Presentation>(presentation);
  presRef.current = presentation;

  const [dod, setDod] = useState<CheckCfg>({ on: false, column: "dod_text", color: "#ffb3b3" });
  const [ceo, setCeo] = useState<CheckCfg>({ on: false, column: "ceo_priority", color: "#b3d4ff" });
  const [popover, setPopover] = useState<"dod" | "ceo" | "subtotal" | null>(null);
  // промежуточные итоги: список (личные, localStorage); черновик для добавления нового
  const [subtotals, setSubtotals] = useState<Subtotal[]>(loadSubtotals);
  const [draftCol, setDraftCol] = useState<string>("total_story_points");
  const [draftFn, setDraftFn] = useState<SubFn>("sum");
  useEffect(() => { saveSubtotals(subtotals); }, [subtotals]);

  useEffect(() => { saveWidths(widths); }, [widths]);
  useEffect(() => { savePalette(palette); }, [palette]);
  useEffect(() => {
    const up = () => { painting.current = false; };
    document.addEventListener("mouseup", up);
    return () => document.removeEventListener("mouseup", up);
  }, []);

  // кисть: снимок-«базис» при включении, отмена по Esc/Ctrl+Z пока кисть в руках
  useEffect(() => {
    if (brushOn) {
      brushBaseline.current = presRef.current;
      undoStack.current = [];
    } else {
      brushBaseline.current = null;
      undoStack.current = [];
    }
  }, [brushOn]);

  useEffect(() => {
    if (!brushOn) return;
    const onKey = (e: KeyboardEvent) => {
      if (editingNote) return;
      // e.code не зависит от раскладки (на русской раскладке e.key для Z = "я")
      if ((e.ctrlKey || e.metaKey) && e.code === "KeyZ") {
        e.preventDefault();
        const prev = undoStack.current.pop();
        if (prev) onPresentation(prev);
      } else if (e.key === "Escape") {
        e.preventDefault();
        if (brushBaseline.current) onPresentation(brushBaseline.current);
        undoStack.current = [];
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [brushOn, editingNote, onPresentation]);

  const rowFills = presentation.row_fills ?? {};
  const cellFills = presentation.cell_fills ?? {};
  const notes = presentation.notes ?? [];

  // --- загрузка платформ: спрос (Σ оценок плана) vs ёмкость метаспринта (Velocity per Meta) ---
  const velocity = grid.velocity_per_meta ?? {};
  const demand: Record<number, number> = {};
  for (const r of rows) {
    for (const [pid, sp] of Object.entries(r.platform_estimates)) {
      demand[+pid] = (demand[+pid] ?? 0) + (Number(sp) || 0);
    }
  }
  // платформы, по которым задана ёмкость — показываем загрузку; перегруз = спрос > ёмкости
  const loadRows = grid.platforms
    .map((p) => ({ p, dem: demand[p.platform_id] ?? 0, cap: velocity[String(p.platform_id)] }))
    .filter((x) => x.cap != null);
  const overloaded = new Set(loadRows.filter((x) => x.dem > (x.cap as number)).map((x) => x.p.platform_id));

  // отображаемые строки = после фильтров по столбцам (демэнд/перегруз считаем по ВСЕМ строкам выше)
  const fRows = anyColFilter
    ? rows.filter((r) => passColFilters(colFilters, r.task as unknown as Record<string, unknown>, r.platform_estimates, grid.platforms))
    : rows;

  // --- промежуточные итоги (сумма/среднее/медиана/мода) по числовому столбцу ---
  const numericCols = cols.filter((c) => c.num);
  function subtotalValues(col: string): number[] {
    const out: number[] = [];
    if (col.startsWith("plat_") || col.startsWith("spr_")) {
      const pid = +col.split("_")[1];
      const isSprint = col.startsWith("spr_");
      const sp = grid.platforms.find((p) => p.platform_id === pid)?.sp_per_sprint;
      for (const r of rows) {
        const v = r.platform_estimates[String(pid)];
        if (v == null) continue;
        out.push(isSprint && sp ? v / sp : v);
      }
    } else {
      for (const r of rows) {
        const raw = (r.task as any)[col];
        const n = Number(raw);
        if (raw != null && raw !== "" && !Number.isNaN(n)) out.push(n);
      }
    }
    return out;
  }
  function calcSubtotal(col: string, fn: SubFn): { value: string; count: number } {
    const xs = subtotalValues(col);
    if (!xs.length) return { value: "—", count: 0 };
    let v: number;
    if (fn === "sum") v = xs.reduce((a, b) => a + b, 0);
    else if (fn === "avg") v = xs.reduce((a, b) => a + b, 0) / xs.length;
    else if (fn === "median") {
      const s = [...xs].sort((a, b) => a - b); const m = Math.floor(s.length / 2);
      v = s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
    } else { // mode
      const freq = new Map<number, number>(); let best = xs[0], bestC = 0;
      for (const x of xs) { const c = (freq.get(x) ?? 0) + 1; freq.set(x, c); if (c > bestC) { bestC = c; best = x; } }
      v = best;
    }
    return { value: numFmt(v), count: xs.length };
  }
  function subLabel(col: string, fn: SubFn): string {
    const fnName = { sum: "Сумма", avg: "Среднее", median: "Медиана", mode: "Мода" }[fn];
    const colName = numericCols.find((c) => c.key === col)?.label
      ?? grid.platforms.find((p) => `plat_${p.platform_id}` === col)?.platform_name
      ?? (grid.platforms.find((p) => `spr_${p.platform_id}` === col) ? `сп: ${grid.platforms.find((p) => `spr_${p.platform_id}` === col)?.platform_name}` : undefined)
      ?? col;
    return `${fnName} · ${colName}`;
  }
  function addSubtotal() {
    setSubtotals([...subtotals, { id: `s${subtotals.length}_${draftCol}_${draftFn}`, col: draftCol, fn: draftFn }]);
  }
  function removeSubtotal(id: string) { setSubtotals(subtotals.filter((s) => s.id !== id)); }

  // --- единый порядок строк (задачи + заметки) ---
  const baseTokens = (() => {
    const order = presentation.order ?? [];
    const taskIds = new Set(fRows.map((r) => r.task.task_id));
    const noteIds = new Set(notes.map((n) => n.id));
    const toks: string[] = [];
    const usedT = new Set<number>(), usedN = new Set<string>();
    for (const tok of order) {
      if (tok.startsWith("t:")) { const id = +tok.slice(2); if (taskIds.has(id)) { toks.push(tok); usedT.add(id); } }
      else if (tok.startsWith("n:")) { const id = tok.slice(2); if (noteIds.has(id)) { toks.push(tok); usedN.add(id); } }
    }
    for (const r of fRows) if (!usedT.has(r.task.task_id)) toks.push(`t:${r.task.task_id}`);
    for (const n of notes) if (!usedN.has(n.id)) toks.push(`n:${n.id}`);
    return toks;
  })();

  const taskById = new Map(fRows.map((r) => [r.task.task_id, r]));
  const noteById = new Map(notes.map((n) => [n.id, n]));
  const manual = sortKey === "";
  const displayTokens = manual ? (dragOrder ?? baseTokens) : baseTokens;

  const items: Item[] = displayTokens.map((tok): Item | null => {
    if (tok.startsWith("t:")) { const r = taskById.get(+tok.slice(2)); return r ? { type: "task", row: r } : null; }
    const n = noteById.get(tok.slice(2)); return n ? { type: "note", note: n } : null;
  }).filter(Boolean) as Item[];

  // при сортировке по колонке — задачи сортируются, заметки в конец
  if (!manual) {
    const taskItems = items.filter((i): i is Extract<Item, { type: "task" }> => i.type === "task");
    taskItems.sort((a, b) => {
      const va = (a.row.task as any)[sortKey] ?? "", vb = (b.row.task as any)[sortKey] ?? "";
      const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va).localeCompare(String(vb), "ru");
      return asc ? cmp : -cmp;
    });
    items.length = 0;
    items.push(...taskItems, ...notes.map((n) => ({ type: "note" as const, note: n })));
  }

  function toggleSort(k: string) { if (k === sortKey) setAsc(!asc); else { setSortKey(k); setAsc(false); } }
  const arrow = (k: string) => (k === sortKey ? (asc ? " ▲" : " ▼") : "");

  function updatePresentation(patch: Partial<Presentation>) { onPresentation({ ...presentation, ...patch }); }

  // --- палитра кисти ---
  function removeColor(i: number) {
    const c = palette[i];
    setPalette(palette.filter((_, j) => j !== i));
    if (brushColor === c) setBrushColor("");
  }

  // --- кисть ---
  function pushUndo() {
    // снимок ДО мазка (один мазок = один шаг отмены)
    undoStack.current.push(presRef.current);
    if (undoStack.current.length > 100) undoStack.current.shift();
  }
  function paint(taskId: number, colKey: string) {
    const key = `${taskId}:${colKey}`;
    const cur = cellFills[key];
    if (brushColor && cur === brushColor) return;
    if (!brushColor && !cur) return;
    const cf = { ...cellFills };
    if (brushColor) cf[key] = brushColor; else delete cf[key];
    updatePresentation({ cell_fills: cf });
  }
  const cellMouse = (taskId: number, colKey: string) => (canEdit && brushOn ? {
    onMouseDown: (e: React.MouseEvent) => { e.preventDefault(); pushUndo(); painting.current = true; paint(taskId, colKey); },
    onMouseEnter: () => { if (painting.current) paint(taskId, colKey); },
  } : {});

  // --- заметки ---
  function addNote() {
    const n: Note = { id: `n${Date.now()}`, text: "", bold: false, fill: "" };
    updatePresentation({ notes: [...notes, n], order: [...baseTokens, `n:${n.id}`] });
  }
  function editNote(id: string, patch: Partial<Note>) {
    updatePresentation({ notes: notes.map((n) => (n.id === id ? { ...n, ...patch } : n)) });
  }
  function delNote(id: string) {
    updatePresentation({ notes: notes.filter((n) => n.id !== id), order: baseTokens.filter((t) => t !== `n:${id}`) });
  }

  // --- drag reorder (задачи и заметки) ---
  function onRowDragOver(e: React.DragEvent, overTok: string) {
    // без preventDefault строка не считается зоной сброса → курсор no-drop (красный круг)
    if (canEdit && manual && dragTok) e.preventDefault();
    if (!canEdit || !manual || !dragTok || dragTok === overTok) return;
    const arr = [...(dragOrder ?? baseTokens)];
    const from = arr.indexOf(dragTok), to = arr.indexOf(overTok);
    if (from < 0 || to < 0) return;
    arr.splice(to, 0, arr.splice(from, 1)[0]);
    setDragOrder(arr);
  }
  function onRowDragEnd() {
    if (canEdit && manual && dragOrder) updatePresentation({ order: dragOrder });
    setDragOrder(null); setDragTok(null);
  }

  // --- перетаскивание столбцов (порядок в localStorage, не в БД) ---
  function onColDrop(overKey: string) {
    if (!dragCol || dragCol === overKey) { setDragCol(null); return; }
    const next = reorderCols(colOrder, dragCol, overKey);
    setColOrder(next); saveColOrder(next); setDragCol(null);
  }

  // --- ресайз колонок ---
  function startResize(e: React.MouseEvent, key: string) {
    e.preventDefault(); e.stopPropagation();
    const startX = e.clientX, startW = colWidth(widths, key);
    const move = (ev: MouseEvent) => setWidths((w) => ({ ...w, [key]: Math.max(36, startW + ev.clientX - startX) }));
    const up = () => { document.removeEventListener("mousemove", move); document.removeEventListener("mouseup", up); };
    document.addEventListener("mousemove", move); document.addEventListener("mouseup", up);
  }

  const wSel = canEdit ? colWidth(widths, "__sel") : 0;
  const wKey = colWidth(widths, "__key");
  const platCount = showPlat ? grid.platforms.length : 0;
  const sprintCount = showSprints ? grid.platforms.length : 0;
  const colspan = (canEdit ? 3 : 2) + cols.length + platCount + sprintCount;

  function cellBg(t: TaskRanked, colKey: string): string | undefined {
    const cf = cellFills[`${t.task_id}:${colKey}`];
    if (cf) return cf;
    if (dod.on && colKey === dod.column && !t.dod_text) return dod.color;
    if (ceo.on && colKey === ceo.column && t.ceo_priority) return ceo.color;
    return rowFills[String(t.task_id)];
  }

  const checkPopover = (which: "dod" | "ceo", cfg: CheckCfg, set: (c: CheckCfg) => void) => (
    <div className="check-pop down" onClick={(e) => e.stopPropagation()}>
      <div className="cp-title">{which === "dod" ? "Проверка DoD (задачи без DoD)" : "Проверка CEO (есть приоритет)"}</div>
      <label className="cp-row">столбец:
        <select value={cfg.column} onChange={(e) => set({ ...cfg, column: e.target.value })}>
          {cols.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
      </label>
      <label className="cp-row">цвет: <input type="color" value={cfg.color} onChange={(e) => set({ ...cfg, color: e.target.value })} /></label>
      <div className="cp-actions">
        <button className="primary" onClick={() => { set({ ...cfg, on: true }); setPopover(null); }}>Применить</button>
        <button onClick={() => { set({ ...cfg, on: false }); setPopover(null); }}>Сбросить</button>
      </div>
    </div>
  );

  return (
    <div className="grid-wrap">
      <div className="plan-toolbar">
        {canEdit && (
          <span className="tb-group">
            <button className={brushOn ? "on" : ""} onClick={() => setBrushOn(!brushOn)} title="Заливка ячеек кистью">🖌 кисть</button>
            {palette.map((c, i) => (
              <span key={i} className={`swatch-wrap${brushColor === c ? " active" : ""}`}
                    onContextMenu={(e) => { e.preventDefault(); removeColor(i); }}>
                <button className="swatch" style={{ background: c }} title="клик — выбрать цвет; × — удалить"
                        onClick={() => { setBrushColor(c); setBrushOn(true); }} />
                <input type="color" value={c} title="изменить цвет"
                       onChange={(e) => { const p = [...palette]; p[i] = e.target.value; setPalette(p); if (brushColor === c) setBrushColor(e.target.value); }} />
                <button className="swatch-del" title="удалить цвет"
                        onClick={(e) => { e.stopPropagation(); removeColor(i); }}>×</button>
              </span>
            ))}
            <button className={`swatch none${brushColor === "" ? " active" : ""}`} title="ластик (снять заливку)" onClick={() => { setBrushColor(""); setBrushOn(true); }} />
            <button className="mini" onClick={() => setPalette([...palette, "#dddddd"])} title="добавить цвет">+</button>
            <button onClick={addNote} title="Добавить строку-заметку">+ заметка</button>
          </span>
        )}
        <span className="tb-group check-wrap">
          <button className={dod.on ? "on" : ""} onClick={() => setPopover(popover === "dod" ? null : "dod")}>Проверка DoD{dod.on ? " ●" : ""}</button>
          {popover === "dod" && checkPopover("dod", dod, setDod)}
          <button className={ceo.on ? "on" : ""} onClick={() => setPopover(popover === "ceo" ? null : "ceo")}>Проверка CEO{ceo.on ? " ●" : ""}</button>
          {popover === "ceo" && checkPopover("ceo", ceo, setCeo)}
          <button className={subtotals.length ? "on" : ""} onClick={() => setPopover(popover === "subtotal" ? null : "subtotal")}>Промежуточные итоги{subtotals.length ? ` ●${subtotals.length}` : ""}</button>
          {popover === "subtotal" && (
            <div className="check-pop down check-pop--wide" onClick={(e) => e.stopPropagation()}>
              <div className="cp-title">Промежуточные итоги (можно несколько)</div>
              {subtotals.length > 0 && (
                <div className="sub-list">
                  {subtotals.map((s) => (
                    <div key={s.id} className="sub-list-row">
                      <span>{subLabel(s.col, s.fn)} = <b>{calcSubtotal(s.col, s.fn).value}</b></span>
                      <button className="pm minus" title="Удалить итог" onClick={() => removeSubtotal(s.id)}>×</button>
                    </div>
                  ))}
                </div>
              )}
              <label className="cp-row">столбец:
                <select value={draftCol} onChange={(e) => setDraftCol(e.target.value)}>
                  {numericCols.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
                  <optgroup label="Оценки платформ">
                    {grid.platforms.map((p) => <option key={`p${p.platform_id}`} value={`plat_${p.platform_id}`}>{p.platform_name}</option>)}
                  </optgroup>
                  <optgroup label="Спринты платформ">
                    {grid.platforms.map((p) => <option key={`s${p.platform_id}`} value={`spr_${p.platform_id}`}>сп: {p.platform_name}</option>)}
                  </optgroup>
                </select>
              </label>
              <label className="cp-row">функция:
                <select value={draftFn} onChange={(e) => setDraftFn(e.target.value as SubFn)}>
                  <option value="sum">Сумма</option>
                  <option value="avg">Среднее</option>
                  <option value="median">Медиана</option>
                  <option value="mode">Мода</option>
                </select>
              </label>
              <div className="cp-actions">
                <button className="primary" onClick={addSubtotal}>+ Добавить итог</button>
                {subtotals.length > 0 && <button onClick={() => setSubtotals([])}>Очистить все</button>}
              </div>
            </div>
          )}
        </span>
        {!manual && <button className="mini" onClick={() => { setSortKey(""); setAsc(false); }}>↕ ручной порядок</button>}
        {anyColFilter && <button className="mini" onClick={() => setColFilters({})} title="Сбросить фильтры по столбцам">✕ фильтры столбцов</button>}
        <span className="spacer" />
        {!canEdit && <span className="lock-note">🔒 только просмотр</span>}
        <span className="muted">строк: {fRows.length}{anyColFilter ? ` из ${rows.length}` : ""}</span>
      </div>

      <div className="plan-total">
        <b>ИТОГО по плану:</b> задач {rows.length} · Σ SP {rows.reduce((s, r) => s + (Number(r.task.total_story_points) || 0), 0)}
        {" · "}Σ EBITDA {money(rows.reduce((s, r) => s + (Number(r.task.adjusted_ebitda) || 0), 0))}
        {grid.plan.plan_status !== "draft" && (
          <span className="frozen-badge" title="План утверждён: показан снимок данных на момент утверждения. Вернуть в «черновик» — снова станет живым и редактируемым.">
            🔒 заморожен (снимок)
          </span>
        )}
      </div>

      {loadRows.length > 0 && (
        <div className="plat-load" title="Спрос (сумма оценок плана) / ёмкость платформы за метаспринт">
          <b>Загрузка платформ:</b>
          {loadRows.map(({ p, dem, cap }) => {
            const over = dem > (cap as number);
            return (
              <span key={p.platform_id} className={`load-chip${over ? " over" : " ok"}`}
                    title={`${p.platform_name}: спрос ${dem} SP, ёмкость ${cap} SP${over ? " — ПЕРЕГРУЗ" : ""}`}>
                {p.platform_name} {dem}/{cap}{over ? " ⚠" : ""}
              </span>
            );
          })}
        </div>
      )}

      {subtotals.length > 0 && (
        <div className="plan-subtotal">
          <b>Промежуточные итоги:</b>
          {subtotals.map((s) => {
            const res = calcSubtotal(s.col, s.fn);
            return (
              <span key={s.id} className="sub-chip" title={`по ${res.count} строкам`}>
                {subLabel(s.col, s.fn)} = <span className="sub-val">{res.value}</span>
                <button className="sub-x" title="Убрать" onClick={() => removeSubtotal(s.id)}>×</button>
              </span>
            );
          })}
        </div>
      )}

      <div className={`grid-scroll${brushOn ? " brush" : ""}`} onClick={() => popover && setPopover(null)}>
        <table className="grid grid--frozen grid--fixed">
          <colgroup>
            {canEdit && <col style={{ width: wSel }} />}
            <col style={{ width: wKey }} />
            <col style={{ width: colWidth(widths, "__summary") }} />
            {cols.map((c) => <col key={c.key} style={{ width: colWidth(widths, c.key) }} />)}
            {showPlat && grid.platforms.map((p) => <col key={p.platform_id} style={{ width: colWidth(widths, "__plat") }} />)}
            {showSprints && grid.platforms.map((p) => <col key={`s${p.platform_id}`} style={{ width: colWidth(widths, "__sprint") }} />)}
          </colgroup>
          <thead>
            <tr>
              {canEdit && <th className="col-sel"></th>}
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
              {showPlat && grid.platforms.map((p, i) => (
                <th key={p.platform_id} className={`col-plat${overloaded.has(p.platform_id) ? " plat-over" : ""}`} title={overloaded.has(p.platform_id) ? `${p.platform_name}: перегруз (спрос ${demand[p.platform_id] ?? 0} > ёмкости ${velocity[String(p.platform_id)]})` : p.platform_name}>{p.platform_name}{overloaded.has(p.platform_id) ? " ⚠" : ""}
                  <ColumnFilter colKey={`plat_${p.platform_id}`} numeric filter={colFilters[`plat_${p.platform_id}`]} onChange={(f) => setColFilter(`plat_${p.platform_id}`, f)} />
                  {i === 0 && <span className="rsz" onMouseDown={(e) => startResize(e, "__plat")} />}
                </th>
              ))}
              {showSprints && grid.platforms.map((p, i) => (
                <th key={`s${p.platform_id}`} className="col-plat col-sprint" title={`спринты по «${p.platform_name}» (velocity ${p.sp_per_sprint} SP/спринт)`}>сп: {p.platform_name}
                  <ColumnFilter colKey={`spr_${p.platform_id}`} numeric filter={colFilters[`spr_${p.platform_id}`]} onChange={(f) => setColFilter(`spr_${p.platform_id}`, f)} />
                  {i === 0 && <span className="rsz" onMouseDown={(e) => startResize(e, "__sprint")} />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((it) => {
              if (it.type === "note") {
                const n = it.note;
                const tok = `n:${n.id}`;
                const noteMouse = canEdit && brushOn ? {
                  onMouseDown: (e: React.MouseEvent) => { e.preventDefault(); pushUndo(); painting.current = true; editNote(n.id, { fill: brushColor || "" }); },
                  onMouseEnter: () => { if (painting.current) editNote(n.id, { fill: brushColor || "" }); },
                } : {};
                return (
                  <tr key={tok} className="note-row" style={n.fill ? { background: n.fill } : undefined}
                      onDragOver={(e) => onRowDragOver(e, tok)} onDrop={onRowDragEnd}>
                    {canEdit && <td className="col-sel" style={n.fill ? { background: n.fill } : undefined}>
                      <span className="drag-h" draggable onDragStart={() => setDragTok(tok)} onDragEnd={onRowDragEnd}>≡</span>
                    </td>}
                    <td className="col-key" style={n.fill ? { background: n.fill } : undefined}>
                      {canEdit && <button className="pm minus" title="Удалить заметку" onClick={() => delNote(n.id)}>×</button>}
                      <span className="note-tag">заметка</span>
                    </td>
                    <td colSpan={colspan - (canEdit ? 2 : 1)} className="note-cell"
                        onDoubleClick={() => canEdit && !brushOn && setEditingNote(n.id)} {...noteMouse}>
                      <span className="note-text" style={{ whiteSpace: "pre-wrap" }}>
                        {n.text || (canEdit ? <span className="muted">двойной клик — ввести текст</span> : "")}
                      </span>
                    </td>
                  </tr>
                );
              }
              const r = it.row, t = r.task, tok = `t:${t.task_id}`;
              const dragRow = canEdit && manual ? { onDragOver: (e: React.DragEvent) => onRowDragOver(e, tok), onDrop: onRowDragEnd } : {};
              return (
                <Fragment key={tok}>
                  <tr className={`${showWarn(t, filters) ? "row-underestimated" : ""}${dragTok === tok ? " dragging" : ""}${selId === t.task_id ? " row-selected" : ""}`}
                      onClick={() => !brushOn && setSelId(selId === t.task_id ? null : t.task_id)}
                      onDoubleClick={() => !brushOn && onOpen(t)} {...dragRow}>
                    {canEdit && (
                      <td className="col-sel" style={rowFills[String(t.task_id)] ? { background: rowFills[String(t.task_id)] } : undefined}>
                        {manual && <span className="drag-h" draggable onDragStart={() => setDragTok(tok)} onDragEnd={onRowDragEnd}>≡</span>}
                      </td>
                    )}
                    <td className="col-key" style={cellBg(t, "jira_key") ? { background: cellBg(t, "jira_key") } : undefined} {...cellMouse(t.task_id, "jira_key")}>
                      {canEdit && <button className="pm minus" title="Убрать из плана" onClick={() => onRemove(t.task_id)}>−</button>}
                      <span className="jira-key">{t.jira_key}</span>
                      {showWarn(t, filters) && <span className="warn" title={warnTitle(t, filters)}>⚠</span>}
                    </td>
                    <td className="col-summary" title={t.task_summary ?? ""} style={cellBg(t, "task_summary") ? { background: cellBg(t, "task_summary") } : undefined} {...cellMouse(t.task_id, "task_summary")}>
                      {t.task_summary ?? "—"}
                    </td>
                    {cols.map((c: Col) => {
                      const bg = cellBg(t, c.key);
                      return <td key={c.key} className={c.num ? "num" : ""} style={bg ? { background: bg } : undefined} {...cellMouse(t.task_id, c.key)}>{c.cell(t)}</td>;
                    })}
                    {showPlat && grid.platforms.map((p) => {
                      const v = r.platform_estimates[String(p.platform_id)];
                      const pk = `plat_${p.platform_id}`;
                      const bg = cellFills[`${t.task_id}:${pk}`];
                      const over = (r.overridden_platforms ?? []).includes(p.platform_id);  // остаток ≠ Jira
                      return <td key={p.platform_id} title={over ? "Изменён остаток (отличается от Jira)" : undefined}
                                 className={`num col-plat${v && !bg ? " plat-filled" : ""}${over ? " cell-overridden" : ""}`}
                                 style={bg ? { background: bg } : undefined} {...cellMouse(t.task_id, pk)}>{v ?? ""}</td>;
                    })}
                    {showSprints && grid.platforms.map((p) => {
                      const v = r.platform_estimates[String(p.platform_id)];
                      const sk = `spr_${p.platform_id}`;
                      const bg = cellFills[`${t.task_id}:${sk}`];
                      const sprints = v != null && p.sp_per_sprint ? v / p.sp_per_sprint : null;
                      return <td key={`s${p.platform_id}`} className={`num col-plat col-sprint${sprints && !bg ? " plat-filled" : ""}`} style={bg ? { background: bg } : undefined} {...cellMouse(t.task_id, sk)}>{sprints ? sprints.toFixed(1) : ""}</td>;
                    })}
                  </tr>
                </Fragment>
              );
            })}
            {items.length === 0 && <tr><td colSpan={colspan} className="empty">План пуст — добавьте задачи из «Автовыгрузки»</td></tr>}
          </tbody>
        </table>
      </div>

      {editingNote && (
        <NoteModal text={noteById.get(editingNote)?.text ?? ""}
                   onSave={(text) => editNote(editingNote, { text })}
                   onClose={() => setEditingNote(null)} />
      )}
    </div>
  );
}
