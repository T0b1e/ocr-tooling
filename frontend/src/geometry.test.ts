import { describe, expect, it } from "vitest";
import { boxFromPoints, columnsToPage, evenColumns, moveBox, pointToNorm, resizeBox } from "./geometry";

describe("geometry", () => {
  it("pointToNorm uses x for width and y for height (non-square)", () => {
    const rect = { left: 100, top: 50, width: 400, height: 800 };
    expect(pointToNorm(300, 450, rect)).toEqual({ x: 0.5, y: 0.5 });
    expect(pointToNorm(120, 90, rect)).toEqual({ x: 0.05, y: 0.05 });
    expect(pointToNorm(-50, 5000, rect)).toEqual({ x: 0, y: 1 });
  });

  it("boxFromPoints emits [y1,x1,y2,x2] in any drag direction", () => {
    expect(boxFromPoints({ x: 0.6, y: 0.2 }, { x: 0.1, y: 0.4 })).toEqual([0.2, 0.1, 0.4, 0.6]);
  });

  it("moveBox keeps size and stays on the page", () => {
    const b = moveBox([0.1, 0.1, 0.2, 0.3], 5, -5);
    expect(b[0]).toBeCloseTo(0); expect(b[2]).toBeCloseTo(0.1);
    expect(b[1]).toBeCloseTo(0.8); expect(b[3]).toBeCloseTo(1);
  });

  it("resizeBox moves only the dragged edges and never inverts", () => {
    expect(resizeBox([0.2, 0.2, 0.4, 0.4], "se", { x: 0.7, y: 0.9 })).toEqual([0.2, 0.2, 0.9, 0.7]);
    const inv = resizeBox([0.2, 0.2, 0.4, 0.4], "nw", { x: 0.9, y: 0.9 });
    expect(inv[0]).toBeLessThan(inv[2]); expect(inv[1]).toBeLessThan(inv[3]);
    expect(resizeBox([0.2, 0.2, 0.4, 0.4], "e", { x: 0.8, y: 0.0 })).toEqual([0.2, 0.2, 0.4, 0.8]);
  });

  it("columns convert from table fractions to page coordinates", () => {
    const cols = columnsToPage([0.3, 0.1, 0.6, 0.5], evenColumns(2, ["a", "b"]));
    expect(cols).toEqual([{ key: "a", x1: 0.1, x2: 0.3 }, { key: "b", x1: 0.3, x2: 0.5 }]);
  });
});
