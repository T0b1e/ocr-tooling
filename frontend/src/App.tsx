import { useMemo, useState } from "react";
import { ApiError, Sample, nextVersion, saveTemplate, uploadSample } from "./api";
import { Canvas } from "./Canvas";
import { Panel } from "./Panel";
import { Box } from "./geometry";
import { Item, localProblems, newItem, toPayload } from "./model";

export default function App() {
  const [sample, setSample] = useState<Sample | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [busy, setBusy] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [preview, setPreview] = useState<{ json: string; version: number } | null>(null);
  const [saved, setSaved] = useState<{ template_id: string; version: number } | null>(null);

  const patch = (id: string, p: Partial<Item>) => setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));
  const remove = (id: string) => { setItems((xs) => xs.filter((x) => x.id !== id)); setSelected(null); };
  const problems = useMemo(() => localProblems(templateId, items), [templateId, items]);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setBusy(true); setErrors([]);
    try { setSample(await uploadSample(file)); setItems([]); setSelected(null); setSaved(null); }
    catch (e) { setErrors(e instanceof ApiError ? e.errors : [String(e)]); }
    finally { setBusy(false); }
  }

  function create(box: Box) {
    const it = newItem(box);
    setItems((xs) => [...xs, it]);
    setSelected(it.id);
  }

  async function openPreview() {
    setErrors([]);
    try {
      const version = await nextVersion(templateId);
      const body = toPayload(sample!.sample_id, templateId, items);
      const doc = {
        template_id: body.template_id, version, status: "draft",
        page_size: { width_px: sample!.width, height_px: sample!.height },
        fingerprint: body.fingerprint, anchors: body.anchors, fields: body.fields,
      };
      setPreview({ json: JSON.stringify(doc, null, 2), version });
    } catch (e) { setErrors(e instanceof ApiError ? e.errors : [String(e)]); }
  }

  async function confirm() {
    setBusy(true); setErrors([]);
    try {
      const out = await saveTemplate(toPayload(sample!.sample_id, templateId, items));
      setSaved({ template_id: out.template_id, version: out.version });
      setPreview(null);
    } catch (e) { setErrors(e instanceof ApiError ? e.errors : [String(e)]); setPreview(null); }
    finally { setBusy(false); }
  }

  if (!sample) {
    return (
      <main className="start">
        <h1>New document type</h1>
        <p>Upload one sample page (image or PDF), then mark the fields.</p>
        <label className="drop">
          <input type="file" accept="image/*,application/pdf" onChange={(e) => onFile(e.target.files?.[0])} disabled={busy} />
          {busy ? "Uploading…" : "Choose a file"}
        </label>
        <div className="modes">
          <div className="mode on"><b>Draw manually</b><span>Drag rectangles on the page. No API key needed.</span></div>
          <div className="mode off"><b>Detect with Gemini</b><span>Coming soon: auto-detect every field, then edit here.</span></div>
        </div>
        {errors.map((e) => <p className="err" key={e}>{e}</p>)}
      </main>
    );
  }

  return (
    <div className="app">
      <header>
        <input className="tid" value={templateId} onChange={(e) => setTemplateId(e.target.value)} placeholder="template id, e.g. invoice-acme" />
        <span className="spacer" />
        <button type="button" onClick={() => { setSample(null); setItems([]); }}>New sample</button>
        <button type="button" className="primary" disabled={busy || problems.length > 0} onClick={openPreview}
          title={problems.join("\n")}>Review &amp; save draft</button>
      </header>
      {saved && <div className="ok">Saved <b>{saved.template_id}</b> v{saved.version} as <b>draft</b>. It becomes active after validation on extra samples.</div>}
      {errors.length > 0 && <div className="err">{errors.map((e) => <div key={e}>{e}</div>)}</div>}
      {problems.length > 0 && <div className="warn"><b>Before you can save:</b> {problems.join(" · ")}</div>}
      <div className="body">
        <Canvas imageUrl={sample.image_url} items={items} selectedId={selected} onSelect={setSelected}
          onChange={(id, box) => patch(id, { box })} onCreate={create} onDelete={remove} />
        <Panel items={items} selectedId={selected} onSelect={setSelected} onPatch={patch} onDelete={remove} />
      </div>
      {preview && (
        <div className="modal" onClick={() => setPreview(null)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>{templateId} · v{preview.version} (draft)</h3>
            <p>This is exactly what will be saved. Coordinates are normalized 0–1, order [y1, x1, y2, x2].</p>
            <pre>{preview.json}</pre>
            <div className="row">
              <button type="button" onClick={() => setPreview(null)}>Back to editing</button>
              <button type="button" className="primary" disabled={busy} onClick={confirm}>Confirm &amp; save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
