/** All box math lives here. Boxes are normalized [y1, x1, y2, x2] (0-1), matching the template schema. */
export type Box = [number, number, number, number];
export type Handle = "nw" | "n" | "ne" | "e" | "se" | "s" | "sw" | "w";

export const MIN_SIZE = 0.005;
const clamp = (v: number, lo = 0, hi = 1) => Math.min(Math.max(v, lo), hi);

/** Pointer position within an element rect -> normalized (x, y). The only px->norm conversion in the UI. */
export function pointToNorm(clientX: number, clientY: number, rect: { left: number; top: number; width: number; height: number }) {
  return { x: clamp((clientX - rect.left) / rect.width), y: clamp((clientY - rect.top) / rect.height) };
}

/** Box spanned by two points (any corner order). */
export function boxFromPoints(a: { x: number; y: number }, b: { x: number; y: number }): Box {
  return [Math.min(a.y, b.y), Math.min(a.x, b.x), Math.max(a.y, b.y), Math.max(a.x, b.x)];
}

/** Translate by (dx, dy) keeping size, clamped inside the page. */
export function moveBox([y1, x1, y2, x2]: Box, dx: number, dy: number): Box {
  const h = y2 - y1, w = x2 - x1;
  const ny = clamp(y1 + dy, 0, 1 - h), nx = clamp(x1 + dx, 0, 1 - w);
  return [ny, nx, ny + h, nx + w];
}

/** Drag a handle to point p; the box never inverts or shrinks below MIN_SIZE. */
export function resizeBox([y1, x1, y2, x2]: Box, handle: Handle, p: { x: number; y: number }): Box {
  if (handle.includes("n")) y1 = clamp(p.y, 0, y2 - MIN_SIZE);
  if (handle.includes("s")) y2 = clamp(p.y, y1 + MIN_SIZE, 1);
  if (handle.includes("w")) x1 = clamp(p.x, 0, x2 - MIN_SIZE);
  if (handle.includes("e")) x2 = clamp(p.x, x1 + MIN_SIZE, 1);
  return [y1, x1, y2, x2];
}

export const round = (n: number) => Math.round(n * 10000) / 10000;
export const roundBox = (b: Box): Box => b.map(round) as Box;

/** Table columns are edited as fractions (0-1) of the table box, exported as page-relative x1/x2. */
export function columnsToPage(box: Box, cols: { key: string; f1: number; f2: number }[]) {
  const [, bx1, , bx2] = box, w = bx2 - bx1;
  return cols.map((c) => ({ key: c.key, x1: round(bx1 + c.f1 * w), x2: round(bx1 + c.f2 * w) }));
}

export function evenColumns(n: number, keys: string[] = []) {
  return Array.from({ length: n }, (_, i) => ({ key: keys[i] ?? `col${i + 1}`, f1: i / n, f2: (i + 1) / n }));
}
