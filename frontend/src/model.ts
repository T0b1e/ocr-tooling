import { Box, columnsToPage, roundBox } from "./geometry";

export type FieldType = "text" | "date" | "number" | "thai_id" | "table" | "checkbox";
export const FIELD_TYPES: FieldType[] = ["text", "date", "number", "thai_id", "table", "checkbox"];
export type AnchorKind = "title" | "logo" | "label";

export type Col = { key: string; f1: number; f2: number }; // fractions of the table box

/** One editable rectangle on the canvas. `role` decides whether it is exported as a field or an anchor. */
export type Item = {
  id: string;
  role: "field" | "anchor";
  box: Box;
  source: "gemini" | "manual";
  // field
  key: string;
  type: FieldType;
  validator: string;
  columns: Col[];
  // anchor
  anchorKind: AnchorKind;
  text: string;
};

let n = 0;
export const newItem = (box: Box, role: Item["role"] = "field", source: Item["source"] = "manual"): Item => ({
  id: `i${Date.now().toString(36)}${n++}`, role, box, source,
  key: "", type: "text", validator: "", columns: [], anchorKind: "label", text: "",
});

/** Build the save payload (everything except the server-assigned version/status/page_size). */
export function toPayload(sampleId: string, templateId: string, items: Item[]) {
  const anchors = items.filter((i) => i.role === "anchor");
  return {
    sample_id: sampleId,
    template_id: templateId.trim(),
    fingerprint: [...new Set(anchors.map((a) => a.text.trim()).filter(Boolean))],
    anchors: anchors.map((a, i) => ({ id: `a${i + 1}`, text: a.text.trim(), kind: a.anchorKind, box: roundBox(a.box) })),
    fields: items.filter((i) => i.role === "field").map((f) => ({
      key: f.key.trim(), type: f.type, box: roundBox(f.box), source: f.source,
      ...(f.validator.trim() ? { validator: f.validator.trim() } : {}),
      ...(f.type === "table" ? { columns: columnsToPage(f.box, f.columns) } : {}),
    })),
  };
}

/** Cheap client-side checks so the user sees problems before the round trip (server remains the authority). */
export function localProblems(templateId: string, items: Item[]): string[] {
  const out: string[] = [];
  if (!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/.test(templateId.trim())) out.push("Template ID: letters, digits, _ . - only");
  const anchors = items.filter((i) => i.role === "anchor");
  if (anchors.length < 2 || anchors.length > 4) out.push(`Mark 2-4 anchors (currently ${anchors.length})`);
  if (anchors.some((a) => !a.text.trim())) out.push("Every anchor needs its text");
  const keys = items.filter((i) => i.role === "field").map((f) => f.key.trim());
  if (keys.some((k) => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(k))) out.push("Every field needs a key (letters, digits, _; not starting with a digit)");
  if (new Set(keys).size !== keys.length) out.push("Field keys must be unique");
  for (const f of items.filter((i) => i.role === "field")) {
    if (f.validator) { try { new RegExp(f.validator); } catch { out.push(`${f.key || "field"}: invalid validator regex`); } }
    if (f.type === "table" && f.columns.length === 0) out.push(`${f.key || "table"}: define at least one column`);
  }
  return out;
}
