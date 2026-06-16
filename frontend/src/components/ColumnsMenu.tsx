import { useEffect, useRef, useState } from "react";
import { BASE_COLS, PLATFORMS_KEY, SPRINTS_KEY } from "./columns";

interface Props {
  hidden: Set<string>;
  onChange: (hidden: Set<string>) => void;
}

export function ColumnsMenu({ hidden, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function toggle(key: string) {
    const h = new Set(hidden);
    h.has(key) ? h.delete(key) : h.add(key);
    onChange(h);
  }
  const items = [
    ...BASE_COLS,
    { key: PLATFORMS_KEY, label: "Платформы — оценки (17)" },
    { key: SPRINTS_KEY, label: "Спринты по платформам (17)" },
  ];

  return (
    <div className="cols-menu" ref={ref}>
      <button className="hb" onClick={() => setOpen(!open)}>Колонки ▾</button>
      {open && (
        <div className="cols-dropdown">
          <div className="cols-actions">
            <button className="mini" onClick={() => onChange(new Set())}>все</button>
            <button className="mini" onClick={() => onChange(new Set(items.map((i) => i.key)))}>ничего</button>
          </div>
          {items.map((c) => (
            <label key={c.key} className="cols-item">
              <input type="checkbox" checked={!hidden.has(c.key)} onChange={() => toggle(c.key)} />
              {c.label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
