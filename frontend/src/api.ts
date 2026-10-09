export type Sample = { sample_id: string; width: number; height: number; image_url: string };

export class ApiError extends Error {
  constructor(public errors: string[], public status: number) {
    super(errors.join("; "));
  }
}

async function parse(r: Response) {
  if (r.ok) return r.json();
  let errors = [`HTTP ${r.status}`];
  try {
    const body = await r.json();
    const d = body.detail;
    if (d?.errors) errors = d.errors;
    else if (typeof d === "string") errors = [d];
    else if (Array.isArray(d)) errors = d.map((e: { loc?: string[]; msg: string }) => `${e.loc?.join(".") ?? ""}: ${e.msg}`);
  } catch { /* non-JSON error body */ }
  throw new ApiError(errors, r.status);
}

export async function uploadSample(file: File): Promise<Sample> {
  const fd = new FormData();
  fd.append("file", file);
  return parse(await fetch("/api/samples", { method: "POST", body: fd }));
}

export async function nextVersion(templateId: string): Promise<number> {
  return (await parse(await fetch(`/api/templates/${encodeURIComponent(templateId)}/next-version`))).version;
}

export async function saveTemplate(body: unknown) {
  return parse(await fetch("/api/templates", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }));
}
