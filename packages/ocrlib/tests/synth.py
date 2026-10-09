"""Synthetic document + deliberate distortions for alignment tests."""
from __future__ import annotations

import cv2
import numpy as np

W, H = 1240, 1754
FONT = cv2.FONT_HERSHEY_SIMPLEX

# normalized [y1,x1,y2,x2]
TITLE = [0.03, 0.35, 0.08, 0.65]
LOGO = [0.02, 0.05, 0.10, 0.22]
LABEL_INV = [0.13, 0.05, 0.16, 0.25]
LABEL_TAX = [0.18, 0.05, 0.21, 0.25]
F_INV = [0.13, 0.30, 0.16, 0.60]
F_TAX = [0.18, 0.30, 0.21, 0.75]
F_DATE = [0.23, 0.30, 0.26, 0.60]
F_PAID = [0.28, 0.30, 0.31, 0.34]
TABLE = [0.35, 0.05, 0.50, 0.95]
COLS = [("desc", 0.05, 0.60), ("qty", 0.60, 0.75), ("amount", 0.75, 0.95)]

VALUES = {"invoice_no": "INV-20431", "tax_id": "1101700230708", "date": "05/03/2567"}


def _px(box):
    y1, x1, y2, x2 = box
    return int(x1 * W), int(y1 * H), int(x2 * W), int(y2 * H)


def _text(img, box, s, scale=1.2, thick=2):
    x1, y1, x2, y2 = _px(box)
    cv2.putText(img, s, (x1 + 6, y2 - 10), FONT, scale, (20, 20, 20), thick, cv2.LINE_AA)


def make_reference(values: dict[str, str] | None = None, paid: bool = True) -> np.ndarray:
    v = {**VALUES, **(values or {})}
    img = np.full((H, W, 3), 255, np.uint8)
    # textured logo (deterministic) so feature detection has something distinctive
    rng = np.random.default_rng(7)
    x1, y1, x2, y2 = _px(LOGO)
    blocks = rng.integers(0, 2, size=((y2 - y1) // 8, (x2 - x1) // 8)) * 200
    img[y1:y1 + blocks.shape[0] * 8, x1:x1 + blocks.shape[1] * 8] = np.kron(blocks, np.ones((8, 8)))[..., None].astype(np.uint8)
    cv2.circle(img, ((x1 + x2) // 2, (y1 + y2) // 2), (y2 - y1) // 3, (30, 30, 160), -1)
    _text(img, TITLE, "INVOICE", 2.2, 4)
    _text(img, LABEL_INV, "Invoice No:")
    _text(img, LABEL_TAX, "Tax ID:")
    _text(img, F_INV, v["invoice_no"])
    _text(img, F_TAX, v["tax_id"])
    _text(img, F_DATE, v["date"])
    x1, y1, x2, y2 = _px(F_PAID)
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
    if paid:
        cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 4)
        cv2.line(img, (x1, y2), (x2, y1), (0, 0, 0), 4)
    tx1, ty1, tx2, ty2 = _px(TABLE)
    rows = [("Widget A", "2", "1,200.00"), ("Gadget B", "10", "350.50"), ("Part C", "1", "99.00")]
    rh = (ty2 - ty1) // 3
    for i, row in enumerate(rows):
        for (key, cx1, cx2), val in zip(COLS, row):
            cv2.putText(img, val, (int(cx1 * W) + 6, ty1 + i * rh + rh // 2 + 10), FONT, 1.0, (20, 20, 20), 2, cv2.LINE_AA)
    # footer distractors
    cv2.putText(img, "Thank you for your business", (80, H - 120), FONT, 1.1, (90, 90, 90), 2, cv2.LINE_AA)
    cv2.putText(img, "Page 1 of 1", (W - 360, H - 60), FONT, 1.0, (90, 90, 90), 2, cv2.LINE_AA)
    return img


def template_dict(reference: np.ndarray, status: str = "draft") -> dict:
    h, w = reference.shape[:2]
    return {
        "template_id": "synthetic-invoice",
        "version": 1,
        "status": status,
        "page_size": {"width_px": w, "height_px": h},
        "fingerprint": ["INVOICE", "Invoice No:", "Tax ID:"],
        "anchors": [
            {"id": "title", "text": "INVOICE", "kind": "title", "box": TITLE},
            {"id": "logo", "text": "", "kind": "logo", "box": LOGO},
            {"id": "lbl_inv", "text": "Invoice No:", "kind": "label", "box": LABEL_INV},
            {"id": "lbl_tax", "text": "Tax ID:", "kind": "label", "box": LABEL_TAX},
        ],
        "fields": [
            {"key": "invoice_no", "type": "text", "box": F_INV, "validator": r"^INV-\d+$"},
            {"key": "tax_id", "type": "thai_id", "box": F_TAX},
            {"key": "date", "type": "date", "box": F_DATE},
            {"key": "paid", "type": "checkbox", "box": F_PAID},
            {"key": "items", "type": "table", "box": TABLE,
             "columns": [{"key": k, "x1": a, "x2": b} for k, a, b in COLS]},
        ],
    }


# ---- distortions: each returns a 3x3 matrix mapping reference px -> scan px ----

def T(tx, ty):
    return np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1]], float)


def S(s):
    return np.diag([s, s, 1.0])


def R(deg, cx=W / 2, cy=H / 2):
    m = cv2.getRotationMatrix2D((cx, cy), deg, 1.0)
    return np.vstack([m, [0, 0, 1]])


def P(px=0.0, py=0.0):
    """Mild perspective (phone photo tilt)."""
    return np.array([[1, 0, 0], [0, 1, 0], [px, py, 1]], float)


def apply(img: np.ndarray, M: np.ndarray, size=None, blur=0, noise=0, seed=0) -> np.ndarray:
    size = size or (img.shape[1], img.shape[0])
    out = cv2.warpPerspective(img, M, size, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(170, 170, 170))
    if blur:
        out = cv2.GaussianBlur(out, (0, 0), blur)
    if noise:
        rng = np.random.default_rng(seed)
        out = np.clip(out.astype(np.int16) + rng.normal(0, noise, out.shape), 0, 255).astype(np.uint8)
    return out
