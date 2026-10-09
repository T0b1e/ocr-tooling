import { FIELD_TYPES, FieldType, Item, AnchorKind } from "./model";
import { evenColumns } from "./geometry";
import { t } from "./i18n";

type Props = {
  items: Item[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onPatch: (id: string, patch: Partial<Item>) => void;
  onDelete: (id: string) => void;
};

export function Panel({ items, selectedId, onSelect, onPatch, onDelete }: Props) {
  const sel = items.find((i) => i.id === selectedId);
  return (
    <aside className="panel">
      <h3>{t("boxes")} ({items.length})</h3>
      <ul className="list">
        {items.map((it) => (
          <li key={it.id} className={it.id === selectedId ? "on" : ""} onClick={() => onSelect(it.id)}>
            <span className={`dot ${it.role}`} />
            <span className="name">{it.role === "anchor" ? `${t("anchorPrefix")}: ${it.text || t("noText")}` : it.key || t("unnamed")}</span>
            <small>{it.role === "field" ? it.type : it.anchorKind}</small>
          </li>
        ))}
        {items.length === 0 && <li className="empty">{t("empty")}</li>}
      </ul>

      {sel && (
        <div className="editor">
          <h3>{t("edit")}</h3>
          <label>{t("useAs")}
            <select value={sel.role} onChange={(e) => onPatch(sel.id, { role: e.target.value as Item["role"] })}>
              <option value="field">{t("roleField")}</option>
              <option value="anchor">{t("roleAnchor")}</option>
            </select>
          </label>
          {sel.role === "anchor" ? (
            <>
              <label>{t("anchorText")}<input value={sel.text} onChange={(e) => onPatch(sel.id, { text: e.target.value })} placeholder={t("anchorTextPh")} /></label>
              <label>{t("kind")}
                <select value={sel.anchorKind} onChange={(e) => onPatch(sel.id, { anchorKind: e.target.value as AnchorKind })}>
                  <option value="title">{t("kindTitle")}</option><option value="logo">{t("kindLogo")}</option><option value="label">{t("kindLabel")}</option>
                </select>
              </label>
            </>
          ) : (
            <>
              <label>{t("key")}<input value={sel.key} onChange={(e) => onPatch(sel.id, { key: e.target.value })} placeholder="invoice_no" /></label>
              <label>{t("type")}
                <select value={sel.type} onChange={(e) => {
                  const type = e.target.value as FieldType;
                  onPatch(sel.id, { type, columns: type === "table" && sel.columns.length === 0 ? evenColumns(3) : sel.columns });
                }}>
                  {FIELD_TYPES.map((t) => <option key={t}>{t}</option>)}
                </select>
              </label>
              <label>{t("validator")}<input value={sel.validator} onChange={(e) => onPatch(sel.id, { validator: e.target.value })} placeholder="^INV-\d+$" /></label>
              {sel.type === "table" && (
                <fieldset>
                  <legend>{t("columns")}</legend>
                  <div className="row">
                    <button type="button" onClick={() => onPatch(sel.id, { columns: evenColumns(sel.columns.length + 1, sel.columns.map((c) => c.key)) })}>{t("addCol")}</button>
                    <button type="button" disabled={sel.columns.length <= 1} onClick={() => onPatch(sel.id, { columns: evenColumns(sel.columns.length - 1, sel.columns.map((c) => c.key)) })}>{t("delCol")}</button>
                  </div>
                  {sel.columns.map((c, i) => (
                    <div className="col" key={i}>
                      <input value={c.key} onChange={(e) => onPatch(sel.id, { columns: sel.columns.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)) })} />
                      <input type="number" step="0.01" min="0" max="1" title={t("colStart")} value={+c.f1.toFixed(3)}
                        onChange={(e) => onPatch(sel.id, { columns: sel.columns.map((x, j) => (j === i ? { ...x, f1: Math.min(+e.target.value, x.f2 - 0.01) } : x)) })} />
                      <input type="number" step="0.01" min="0" max="1" title={t("colEnd")} value={+c.f2.toFixed(3)}
                        onChange={(e) => onPatch(sel.id, { columns: sel.columns.map((x, j) => (j === i ? { ...x, f2: Math.max(+e.target.value, x.f1 + 0.01) } : x)) })} />
                    </div>
                  ))}
                  <small>{t("tableHint")}</small>
                </fieldset>
              )}
            </>
          )}
          <button type="button" className="danger" onClick={() => onDelete(sel.id)}>{t("del")}</button>
        </div>
      )}
    </aside>
  );
}
