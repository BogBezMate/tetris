import { useEffect, useRef, useState } from "react";
import type { Filters } from "./columns";

interface Props {
  filters: Filters;
  onChange: (f: Filters) => void;
  counts?: Record<string, number>;  // по ключам ROWS: сколько задач в каждой категории
}

const ROWS: { key: string; label: string; show: keyof Filters; warn: keyof Filters }[] = [
  { key: "under", label: "Недооценённые (нет оценки у выбранной платформы)", show: "showUnderestimated", warn: "warnUnderestimated" },
  { key: "unplat", label: "Без платформ и без оценок (пусто)", show: "showUnplatformed", warn: "warnUnplatformed" },
  { key: "noteam", label: "Есть оценка, но команда не выбрана", show: "showEstimateNoTeam", warn: "warnEstimateNoTeam" },
  { key: "unsel", label: "Оценка у невыбранной платформы (есть и выбранные)", show: "showUnselectedEstimate", warn: "warnUnselectedEstimate" },
];

/** Фильтр задач по оценённости. На каждую причину 2 галочки: показывать задачи и показывать ⚠. */
export function FilterMenu({ filters, onChange, counts }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  // активен, если хоть одна из галочек снята
  const active = ROWS.some((r) => !filters[r.show] || !filters[r.warn]);

  return (
    <div className="cols-menu" ref={ref}>
      <button className={`hb${active ? " on" : ""}`} onClick={() => setOpen(!open)} title="Фильтр недооценённых задач">
        Фильтр{active ? " ●" : ""} ▾
      </button>
      {open && (
        <div className="cols-dropdown filter-dropdown">
          <div className="filter-head">
            <span className="filter-cause">Причина</span>
            <span className="filter-col">показывать</span>
            <span className="filter-col">значок ⚠</span>
          </div>
          {ROWS.map((r) => (
            <div key={r.key} className="filter-row">
              <span className="filter-cause">{r.label}
                {counts && <span className="filter-count">{counts[r.key] ?? 0}</span>}
              </span>
              <span className="filter-col">
                <input type="checkbox" checked={filters[r.show]}
                       title="Показывать такие задачи"
                       onChange={() => onChange({ ...filters, [r.show]: !filters[r.show] })} />
              </span>
              <span className="filter-col">
                <input type="checkbox" checked={filters[r.warn]}
                       title="Показывать значок ⚠ с подписью"
                       onChange={() => onChange({ ...filters, [r.warn]: !filters[r.warn] })} />
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
