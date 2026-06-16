import { useState } from "react";

interface Props {
  text: string;
  onSave: (text: string) => void;
  onClose: () => void;
}

export function NoteModal({ text, onSave, onClose }: Props) {
  const [value, setValue] = useState(text);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal--note" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-title">Заметка</div>
          <button className="x" onClick={onClose}>✕</button>
        </div>
        <div className="note-modal-body">
          <textarea className="note-modal-area" value={value} placeholder="введите текст" autoFocus
                    onChange={(e) => setValue(e.target.value)} />
        </div>
        <div className="modal-foot">
          <span className="spacer" />
          <button onClick={onClose}>Отменить</button>
          <button className="primary" onClick={() => { onSave(value); onClose(); }}>Сохранить</button>
        </div>
      </div>
    </div>
  );
}
