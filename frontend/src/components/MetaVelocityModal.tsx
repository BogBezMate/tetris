import { useEffect, useState } from "react";
import { api } from "../api";
import type { QuarterVelocity } from "../types";

interface Props {
  quarterId: number;
  quarterName: string;
  onClose: () => void;
  onSaved: () => void;
  flash: (m: string) => void;
}

/** Velocity платформ в метаспринте — два числа на платформу:
 *  - ёмкость за метаспринт (для подсветки перегруза: спрос > ёмкости → красным);
 *  - SP за спринт (делитель для колонок «спринты» и «МАКС спринтов»).
 *  Пусто = значение по умолчанию (без лимита / глобальный делитель 5-6). */
export function MetaVelocityModal({ quarterId, quarterName, onClose, onSaved, flash }: Props) {
  const [rows, setRows] = useState<QuarterVelocity[]>([]);
  const [cap, setCap] = useState<Record<number, string>>({});
  const [sps, setSps] = useState<Record<number, string>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.quarterVelocity(quarterId).then((rs) => {
      setRows(rs);
      const c: Record<number, string> = {}, s: Record<number, string> = {};
      for (const r of rs) {
        c[r.platform_id] = r.capacity_sp != null ? String(r.capacity_sp) : "";
        s[r.platform_id] = r.sp_per_sprint != null ? String(r.sp_per_sprint) : "";
      }
      setCap(c); setSps(s);
    }).catch((e) => flash(e instanceof Error ? e.message : "Ошибка"));
  }, [quarterId]);

  async function save() {
    setBusy(true);
    try {
      const items = rows.map((r) => {
        const cr = (cap[r.platform_id] ?? "").trim();
        const sr = (sps[r.platform_id] ?? "").trim();
        return {
          platform_id: r.platform_id,
          capacity_sp: cr === "" ? null : Number(cr),
          sp_per_sprint: sr === "" ? null : Number(sr),
        };
      });
      await api.saveQuarterVelocity(quarterId, items);
      flash("Velocity метаспринта сохранена");
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
          <div className="modal-title">Velocity метаспринта «{quarterName}» — по платформам</div>
          <button className="x" onClick={onClose}>✕</button>
        </div>
        <div className="velocity-body">
          <div className="velo-grid velo-head">
            <span>Платформа</span>
            <span title="Сколько SP платформа осилит за весь метаспринт (для подсветки перегруза)">Ёмкость, SP</span>
            <span title="Делитель: сколько SP «откусываем» за один спринт (колонки «спринты»)">SP/спринт</span>
          </div>
          {rows.map((r) => (
            <div key={r.platform_id} className="velo-grid">
              <span className="velo-name">{r.platform_name}</span>
              <input type="number" step="1" min="0" placeholder="без лимита"
                     value={cap[r.platform_id] ?? ""}
                     onChange={(e) => setCap({ ...cap, [r.platform_id]: e.target.value })} />
              <input type="number" step="0.5" min="0.5" placeholder={String(r.sp_per_sprint_default)}
                     value={sps[r.platform_id] ?? ""}
                     onChange={(e) => setSps({ ...sps, [r.platform_id]: e.target.value })} />
            </div>
          ))}
        </div>
        <div className="modal-foot">
          <span className="muted">Пусто — значение по умолчанию (ёмкость без лимита, делитель {rows[0]?.sp_per_sprint_default ?? 5}). Перегруз подсвечивается красным.</span>
          <span className="spacer" />
          <button onClick={onClose}>Отменить</button>
          <button className="primary" onClick={save} disabled={busy}>Сохранить</button>
        </div>
      </div>
    </div>
  );
}
