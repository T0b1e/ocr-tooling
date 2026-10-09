import { useRef, useState } from "react";
import { Box, Handle, boxFromPoints, moveBox, pointToNorm, resizeBox, MIN_SIZE } from "./geometry";
import { Item } from "./model";

const HANDLES: Handle[] = ["nw", "n", "ne", "e", "se", "s", "sw", "w"];

type Drag =
  | { kind: "draw"; start: { x: number; y: number }; box: Box }
  | { kind: "move"; id: string; last: { x: number; y: number } }
  | { kind: "resize"; id: string; handle: Handle };

type Props = {
  imageUrl: string;
  items: Item[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  onChange: (id: string, box: Box) => void;
  onCreate: (box: Box) => void;
  onDelete: (id: string) => void;
};

export function Canvas({ imageUrl, items, selectedId, onSelect, onChange, onCreate, onDelete }: Props) {
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<Drag | null>(null);
  const [draft, setDraft] = useState<Box | null>(null);

  const norm = (e: React.PointerEvent) => pointToNorm(e.clientX, e.clientY, stage.current!.getBoundingClientRect());

  function begin(e: React.PointerEvent, d: Drag) {
    e.stopPropagation();
    stage.current!.setPointerCapture(e.pointerId);
    drag.current = d;
  }

  function onMove(e: React.PointerEvent) {
    const d = drag.current;
    if (!d) return;
    const p = norm(e);
    if (d.kind === "draw") {
      const box = boxFromPoints(d.start, p);
      d.box = box;
      setDraft(box);
    } else {
      const it = items.find((i) => i.id === d.id);
      if (!it) return;
      if (d.kind === "move") {
        onChange(d.id, moveBox(it.box, p.x - d.last.x, p.y - d.last.y));
        d.last = p;
      } else {
        onChange(d.id, resizeBox(it.box, d.handle, p));
      }
    }
  }

  function onUp() {
    const d = drag.current;
    drag.current = null;
    if (d?.kind === "draw") {
      const [y1, x1, y2, x2] = d.box;
      if (y2 - y1 > MIN_SIZE * 2 && x2 - x1 > MIN_SIZE * 2) onCreate(d.box);
      setDraft(null);
    }
  }

  function onKey(e: React.KeyboardEvent) {
    if (!selectedId) return;
    const it = items.find((i) => i.id === selectedId);
    if (!it) return;
    if (e.key === "Delete" || e.key === "Backspace") { onDelete(selectedId); e.preventDefault(); return; }
    const step = e.shiftKey ? 0.01 : 0.002;
    const d: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (d[e.key]) { onChange(selectedId, moveBox(it.box, ...d[e.key])); e.preventDefault(); }
  }

  const pos = ([y1, x1, y2, x2]: Box) => ({ left: `${x1 * 100}%`, top: `${y1 * 100}%`, width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%` });

  return (
    <div className="stage-wrap">
      <div
        className="stage" ref={stage} tabIndex={0} onKeyDown={onKey}
        onPointerDown={(e) => { onSelect(null); begin(e, { kind: "draw", start: norm(e), box: [0, 0, 0, 0] }); }}
        onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={onUp}
      >
        <img src={imageUrl} alt="document sample" draggable={false} />
        {items.map((it) => {
          const sel = it.id === selectedId;
          const [y1, x1, y2, x2] = it.box;
          return (
            <div
              key={it.id}
              className={`box ${it.role} ${sel ? "sel" : ""}`}
              style={pos(it.box)}
              onPointerDown={(e) => { onSelect(it.id); begin(e, { kind: "move", id: it.id, last: norm(e) }); stage.current?.focus(); }}
            >
              <span className="tag">{it.role === "anchor" ? `⚓ ${it.text || it.anchorKind}` : it.key || it.type}</span>
              {it.role === "field" && it.type === "table" && it.columns.slice(1).map((c) => (
                <i key={c.key + c.f1} className="colline" style={{ left: `${c.f1 * 100}%` }} />
              ))}
              {sel && HANDLES.map((h) => (
                <b key={h} className={`handle ${h}`} data-box={`${y1},${x1},${y2},${x2}`}
                  onPointerDown={(e) => begin(e, { kind: "resize", id: it.id, handle: h })} />
              ))}
            </div>
          );
        })}
        {draft && <div className="box draft" style={pos(draft)} />}
      </div>
      <p className="hint">Drag on the page to draw a box · click a box to select · drag to move · handles to resize · arrows nudge (Shift = bigger) · Delete removes</p>
    </div>
  );
}
