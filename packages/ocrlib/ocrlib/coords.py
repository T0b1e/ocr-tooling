"""The only place coordinate conventions are converted.

Conventions:
- Gemini ``box_2d``: ``[ymin, xmin, ymax, xmax]`` on a 0-1000 scale.
- Template box:      ``[y1, x1, y2, x2]`` normalized 0-1 (same axis order as Gemini).
- Pixel rect (OpenCV/numpy slicing): ``(x1, y1, x2, y2)`` -- x first!
"""
from __future__ import annotations

import math
from typing import Sequence

GEMINI_SCALE = 1000.0


def gemini_box_to_norm(box_2d: Sequence[float]) -> list[float]:
    """Convert a Gemini ``[ymin,xmin,ymax,xmax]`` 0-1000 box to normalized ``[y1,x1,y2,x2]``.

    Values are clamped to [0,1]; reversed corners are re-ordered.
    Raises ValueError for malformed or degenerate (zero-area) boxes.
    """
    if len(box_2d) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box_2d):
        raise ValueError(f"box_2d must be 4 finite numbers, got {box_2d!r}")
    ymin, xmin, ymax, xmax = (min(max(v / GEMINI_SCALE, 0.0), 1.0) for v in box_2d)
    y1, y2 = sorted((ymin, ymax))
    x1, x2 = sorted((xmin, xmax))
    if y1 == y2 or x1 == x2:
        raise ValueError(f"degenerate box_2d {list(box_2d)!r}")
    return [y1, x1, y2, x2]


def norm_to_px(box: Sequence[float], width: int, height: int) -> tuple[int, int, int, int]:
    """Normalized ``[y1,x1,y2,x2]`` -> pixel ``(x1, y1, x2, y2)``, clipped to the image."""
    y1, x1, y2, x2 = box
    px1, px2 = (min(max(round(v * width), 0), width) for v in (x1, x2))
    py1, py2 = (min(max(round(v * height), 0), height) for v in (y1, y2))
    return px1, py1, px2, py2


def px_to_norm(rect: Sequence[float], width: int, height: int) -> list[float]:
    """Pixel ``(x1, y1, x2, y2)`` -> normalized ``[y1,x1,y2,x2]`` (clamped, re-ordered)."""
    x1, y1, x2, y2 = rect
    nx1, nx2 = sorted(min(max(v / width, 0.0), 1.0) for v in (x1, x2))
    ny1, ny2 = sorted(min(max(v / height, 0.0), 1.0) for v in (y1, y2))
    return [ny1, nx1, ny2, nx2]
