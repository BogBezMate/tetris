import { useEffect, useState } from "react";
import { api } from "../api";
import type { PlatformRef } from "../types";

interface Props {
  onClose: () => void;
  onSaved: () => void;
  flash: (m: string) => void;
}

export function VelocityModal({ onClose, onSaved, flash }: Props) {
  const [platforms, setPlatforms] = useState<PlatformRef[]>([]);
  const [vals, setVals] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.platforms().then((ps) => {
      setPlatforms(ps);
      const v: Record<number, string> = {};
      for (const p of ps) v[p.platform_id] = String(p.sp_per_sprint);
      setVals(v);
    }).catch((e) => flash(e instanceof Error ? e.message : "Ошибка"));
  }, []);

  async function save() {
    setBusy(true);
    try {
      const items = platforms.map((p) => ({
        platform_id: p.platform_id,
        sp_per_sprint: Number(vals[p.platform_id] || 0) || 1,
      }));
      await api.saveVelocity(items);
      flash("Velocity сохранена");
      onSaved();
      onClose();
    } catch (e) {
      flash(e instanceof Error ? e.message : "Ошибка");
    } finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal--velocity" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-title">Velocity платформ — сколько SP в спринт «откусываем» от задачи</div>
          <button className="x" onClick={onClose}>✕</button>
        </div>
        <div className="velocity-body">
          {platforms.map((p) => (
            <label key={p.platform_id} className="jff jff--inline">
              <span className="jff-label">{p.platform_name}</span>
              <input type="number" step="0.5" min="0.5" value={vals[p.platform_id] ?? ""}
                     onChange={(e) => setVals({ ...vals, [p.platform_id]: e.target.value })} />
            </label>
          ))}
        </div>
        <div className="modal-foot">
          <span className="muted">Используется в формуле: спринты = оценка ÷ velocity</span>
          <span className="spacer" />
          <button onClick={onClose}>Отменить</button>
          <button className="primary" onClick={save} disabled={busy}>Сохранить</button>
        </div>
      </div>
    </div>
  );
}
