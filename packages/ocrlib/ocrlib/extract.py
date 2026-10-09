"""Runtime extraction: align a scan to a template, crop each field, OCR, normalise."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from .align import Alignment, AlignmentError, estimate_transform, rectify
from .coords import norm_to_px
from .imageio import ImageLike, load_image
from .ocr import OcrEngine
from .schema.models import Field_, Template, validate_template
from .validators import (
    check_pattern,
    normalize_date,
    normalize_number,
    normalize_text,
    normalize_thai_id,
)

__all__ = ["extract", "extract_detailed", "ExtractResult", "AlignmentError"]

CHECKBOX_INK_THRESHOLD = 0.08
MIN_OCR_HEIGHT = 48  # crops shorter than this are upscaled for the OCR engine


@dataclass
class ExtractResult:
    fields: dict[str, dict[str, Any]]
    alignment: Alignment


def _prep(crop: np.ndarray) -> np.ndarray:
    """White border + upscale small crops; keeps BGR so any engine can consume it."""
    if crop.shape[0] < MIN_OCR_HEIGHT:
        s = MIN_OCR_HEIGHT / crop.shape[0]
        crop = cv2.resize(crop, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(crop, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))


def _crop(img: np.ndarray, box) -> np.ndarray:
    h, w = img.shape[:2]
    x1, y1, x2, y2 = norm_to_px(box, w, h)
    return img[y1:max(y2, y1 + 1), x1:max(x2, x1 + 1)]


def _checkbox(crop: np.ndarray) -> tuple[bool, float]:
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    h, w = bw.shape
    inner = bw[int(h * 0.2):max(int(h * 0.8), int(h * 0.2) + 1), int(w * 0.2):max(int(w * 0.8), int(w * 0.2) + 1)]
    ratio = float(inner.mean() / 255.0)
    checked = ratio > CHECKBOX_INK_THRESHOLD
    margin = abs(ratio - CHECKBOX_INK_THRESHOLD) / CHECKBOX_INK_THRESHOLD
    return checked, float(min(1.0, 0.5 + margin / 2))


def _table_rows(crop: np.ndarray, f: Field_, ocr: OcrEngine) -> tuple[list[dict[str, str]], float]:
    g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    # drop long ruling lines so they don't glue rows together
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (max(bw.shape[1] // 2, 3), 1))
    bw = cv2.subtract(bw, cv2.morphologyEx(bw, cv2.MORPH_OPEN, k))
    prof = (bw > 0).sum(axis=1) > max(1, 0.004 * bw.shape[1])
    rows, start = [], None
    for y, on in enumerate(list(prof) + [False]):
        if on and start is None:
            start = y
        elif not on and start is not None:
            if y - start >= 4:
                rows.append((start, y))
            start = None
    # merge bands separated by tiny gaps (e.g. Thai vowels/tone marks)
    merged: list[list[int]] = []
    for a, b in rows:
        if merged and a - merged[-1][1] < 4:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    _, bx1, _, bx2 = f.box
    out, confs = [], []
    for a, b in merged:
        row = {}
        for c in f.columns or []:
            cx1 = int(round((c.x1 - bx1) / (bx2 - bx1) * crop.shape[1]))
            cx2 = int(round((c.x2 - bx1) / (bx2 - bx1) * crop.shape[1]))
            cell = crop[max(a - 2, 0):b + 2, max(cx1, 0):max(cx2, cx1 + 1)]
            r = ocr.read(_prep(cell))
            row[c.key] = normalize_text(r.text)[0]
            confs.append(r.confidence)
        out.append(row)
    return out, float(np.mean(confs)) if confs else 0.0


def _read_field(f: Field_, crop: np.ndarray, ocr: OcrEngine) -> dict[str, Any]:
    if f.type == "checkbox":
        checked, conf = _checkbox(crop)
        return {"value": checked, "confidence": conf, "valid": None}
    if f.type == "table":
        rows, conf = _table_rows(crop, f, ocr)
        return {"value": rows, "confidence": conf, "valid": bool(rows)}
    r = ocr.read(_prep(crop))
    norm = {"thai_id": normalize_thai_id, "date": normalize_date, "number": normalize_number}.get(f.type, normalize_text)
    value, valid = norm(r.text)
    pattern_ok = check_pattern(f.validator, value)
    conf = r.confidence
    if pattern_ok is False:
        valid, conf = False, conf * 0.5
    elif not valid:
        conf *= 0.7
    return {"value": value, "confidence": float(conf), "valid": valid if (f.type != "text" or pattern_ok is not None) else None}


def extract_detailed(image: ImageLike, template: Template | dict, reference: ImageLike, ocr: OcrEngine) -> ExtractResult:
    """Align ``image`` to ``template`` (using its ``reference`` page) and read every field.

    Field confidence is the OCR confidence capped by the alignment confidence.
    Raises AlignmentError if the anchors cannot be found.
    """
    if isinstance(template, dict):
        template = validate_template(template)
    scan, ref = load_image(image), load_image(reference)
    alignment = estimate_transform(ref, scan, template)
    flat = rectify(scan, alignment)
    fields = {}
    for f in template.fields:
        res = _read_field(f, _crop(flat, f.box), ocr)
        res["confidence"] = float(min(res["confidence"], alignment.confidence))
        fields[f.key] = res
    return ExtractResult(fields, alignment)


def extract(image: ImageLike, template: Template | dict, reference: ImageLike, ocr: OcrEngine) -> dict[str, dict[str, Any]]:
    """``{field_key: {"value", "confidence", "valid"}}``. See :func:`extract_detailed`."""
    return extract_detailed(image, template, reference, ocr).fields
