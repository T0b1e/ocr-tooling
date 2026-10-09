import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ApiError, Sample, nextVersion, saveTemplate, uploadSample } from "./api";
import { Canvas } from "./Canvas";
import { Panel } from "./Panel";
import { Box } from "./geometry";
import { t, getLang, setLang } from "./i18n";
import { Item, localProblems, newItem, toPayload } from "./model";

function reportError(e: unknown, title: string) {
  const messages = e instanceof ApiError ? e.errors : [e instanceof Error ? e.message : String(e)];
  toast.error(title, { description: messages.join("\n"), duration: 8000 });
}

export default function App() {
  const [sample, setSample] = useState<Sample | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<{ json: string; version: number } | null>(null);
  const [, rerender] = useState(0);
  const toggleLang = () => { setLang(getLang() === "th" ? "en" : "th"); rerender((n) => n + 1); };
  const [saved, setSaved] = useState<{ template_id: string; version: number } | null>(null);

  const patch = (id: string, p: Partial<Item>) => setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));
  const remove = (id: string) => { setItems((xs) => xs.filter((x) => x.id !== id)); setSelected(null); };
  const problems = useMemo(() => localProblems(templateId, items), [templateId, items]);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try { setSample(await uploadSample(file)); setItems([]); setSelected(null); setSaved(null); }
    catch (e) { reportError(e, t("errUpload")); }
    finally { setBusy(false); }
  }

  function create(box: Box) {
    const it = newItem(box);
    setItems((xs) => [...xs, it]);
    setSelected(it.id);
  }

  async function openPreview() {
    try {
      const version = await nextVersion(templateId);
      const body = toPayload(sample!.sample_id, templateId, items);
      const doc = {
        template_id: body.template_id, version, status: "draft",
        page_size: { width_px: sample!.width, height_px: sample!.height },
        fingerprint: body.fingerprint, anchors: body.anchors, fields: body.fields,
      };
      setPreview({ json: JSON.stringify(doc, null, 2), version });
    } catch (e) { reportError(e, t("errPrepare")); }
  }

  async function confirm() {
    setBusy(true);
    try {
      const out = await saveTemplate(toPayload(sample!.sample_id, templateId, items));
      setSaved({ template_id: out.template_id, version: out.version });
      toast.success(t("savedToast")(out.template_id, out.version));
      setPreview(null);
    } catch (e) { reportError(e, t("errSave")); setPreview(null); }
    finally { setBusy(false); }
  }

  const langBtn = <button type="button" className="ghost" onClick={toggleLang}>{t("lang")}</button>;

  if (!sample) {
    return (
      <main className="start">
        <div className="start-top">{langBtn}</div>
        <h1>{t("title")}</h1>
        <p className="lead">{t("startHint")}</p>
        <label className="drop">
          <input type="file" accept="image/*,application/pdf" onChange={(e) => onFile(e.target.files?.[0])} disabled={busy} />
          {busy ? t("uploading") : t("choose")}
        </label>
        <div className="modes">
          <div className="mode on"><b>{t("modeManual")}</b><span>{t("modeManualDesc")}</span></div>
          <div className="mode off"><b>{t("modeGemini")}</b><span>{t("modeGeminiDesc")}</span></div>
        </div>
      </main>
    );
  }

  return (
    <div className="app">
      <header>
        <input className="tid" value={templateId} onChange={(e) => setTemplateId(e.target.value)} placeholder={t("templateId")} />
        <span className="spacer" />
        {langBtn}
        <button type="button" className="ghost" onClick={() => { setSample(null); setItems([]); }}>{t("newSample")}</button>
        <button type="button" className="primary" disabled={busy || problems.length > 0} onClick={openPreview}
          title={problems.join("\n")}>{t("review")}</button>
      </header>
      {saved && <div className="ok">{t("saved")(saved.template_id, saved.version)}</div>}
      {problems.length > 0 && <div className="warn"><b>{t("before")}</b> {problems.join(" · ")}</div>}
      <div className="body">
        <Canvas imageUrl={sample.image_url} items={items} selectedId={selected} onSelect={setSelected}
          onChange={(id, box) => patch(id, { box })} onCreate={create} onDelete={remove} />
        <Panel items={items} selectedId={selected} onSelect={setSelected} onPatch={patch} onDelete={remove} />
      </div>
      {preview && (
        <div className="modal" onClick={() => setPreview(null)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>{templateId} · v{preview.version} ({t("draft")})</h3>
            <p>{t("previewNote")}</p>
            <pre>{preview.json}</pre>
            <div className="row">
              <button type="button" onClick={() => setPreview(null)}>{t("back")}</button>
              <button type="button" className="primary" disabled={busy} onClick={confirm}>{t("confirm")}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
