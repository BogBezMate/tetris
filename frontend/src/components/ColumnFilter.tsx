import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { colFilterActive, type ColFilter } from "./columns";

interface Props {
  colKey: string;
  numeric: boolean;            // числовой столбец (платформы/спринты/числа) → «только с значением» + мин/макс
  filter?: ColFilter;
  onChange: (f: ColFilter | undefined) => void;
}

/** Воронка-фильтр у заголовка столбца. Поповер позиционируется fixed — не обрезается таблицей. */
export function ColumnFilter({ numeric, filter, onChange }: Props) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const iconRef = useRef<HTMLSpanElement>(null);
  const popRef = useRef<HTMLDivElement>(null);
  const f = filter ?? {};
  const active = colFilterActive(filter);

  function toggle(e: React.MouseEvent) {
    e.stopPropagation();
    if (pos) { setPos(null); return; }
    const r = iconRef.current!.getBoundingClientRect();
    const left = Math.min(r.right - 8, window.innerWidth - 190);   // не вылезать за правый край
    setPos({ top: r.bottom + 4, left: Math.max(8, left) });
  }

  useEffect(() => {
    if (!pos) return;
    function onDoc(e: MouseEvent) {
      if (popRef.current && !popRef.current.contains(e.target as Node)
          && iconRef.current && !iconRef.current.contains(e.target as Node)) setPos(null);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [pos]);

  const upd = (patch: Partial<ColFilter>) => onChange({ ...f, ...patch });
  const numOrNull = (s: string) => (s.trim() === "" ? null : Number(s));

  return (
    <>
      <span ref={iconRef} className={`colf-icon${active ? " active" : ""}`}
            title="Фильтр столбца" onClick={toggle}>▼</span>
      {pos && createPortal(
        <div ref={popRef} className="colf-pop" style={{ top: pos.top, left: pos.left }}
             onClick={(e) => e.stopPropagation()}>
          <div className="colf-title">Фильтр столбца</div>
          {numeric ? (
            <>
              <label className="colf-row">
                <input type="checkbox" checked={!!f.hasValue} onChange={(e) => upd({ hasValue: e.target.checked })} />
                только с значением
              </label>
              <label className="colf-row"><span>от</span><input type="number" value={f.min ?? ""} onChange={(e) => upd({ min: numOrNull(e.target.value) })} /></label>
              <label className="colf-row"><span>до</span><input type="number" value={f.max ?? ""} onChange={(e) => upd({ max: numOrNull(e.target.value) })} /></label>
            </>
          ) : (
            <label className="colf-row"><span>содержит</span>
              <input type="text" value={f.contains ?? ""} onChange={(e) => upd({ contains: e.target.value })} />
            </label>
          )}
          <div className="colf-actions">
            <button onClick={() => { onChange(undefined); setPos(null); }}>сбросить</button>
            <button className="primary" onClick={() => setPos(null)}>ок</button>
          </div>
        </div>,
        document.body
      )}
    </>
  );
}
