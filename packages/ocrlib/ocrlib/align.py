"""Locate template anchors in a scan and estimate the reference->scan transform.

Pipeline: SIFT features on the reference page restricted to the anchor boxes are matched
against the whole scan; RANSAC fits a homography (similarity fallback). If the anchors alone
give too few matches we retry with the whole reference page. The result is verified by
comparing each anchor region of the rectified scan with the reference (normalised correlation).

``H`` always maps *reference pixels* -> *scan pixels*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import cv2
import numpy as np

from .coords import norm_to_px
from .schema.models import Template

MAX_SIDE = 1600  # feature detection runs on images downscaled to this long side


class AlignmentError(RuntimeError):
    """Raised when the scan cannot be aligned to the template reference."""


@dataclass
class Alignment:
    H: np.ndarray                      # 3x3, reference px -> scan px
    ref_size: tuple[int, int]          # (width, height) of the reference
    method: str                        # "homography" | "similarity"
    matches: int
    inliers: int
    used_anchors_only: bool
    anchor_scores: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


def _gray(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img


def _downscale(gray: np.ndarray) -> tuple[np.ndarray, float]:
    s = min(1.0, MAX_SIDE / max(gray.shape[:2]))
    if s == 1.0:
        return gray, 1.0
    return cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), s


def _anchor_mask(shape: tuple[int, int], template: Template, pad: float = 0.01) -> np.ndarray:
    h, w = shape
    mask = np.zeros((h, w), np.uint8)
    for a in template.anchors:
        y1, x1, y2, x2 = a.box
        box = [max(y1 - pad, 0), max(x1 - pad, 0), min(y2 + pad, 1), min(x2 + pad, 1)]
        px1, py1, px2, py2 = norm_to_px(box, w, h)
        mask[py1:py2, px1:px2] = 255
    return mask


def _match(ref_g, scan_g, mask, ratio: float = 0.75):
    det = cv2.SIFT_create(nfeatures=4000)
    k1, d1 = det.detectAndCompute(ref_g, mask)
    k2, d2 = det.detectAndCompute(scan_g, None)
    if d1 is None or d2 is None or len(k1) < 4 or len(k2) < 4:
        return [], [], []
    knn = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [m for m, n in (p for p in knn if len(p) == 2) if m.distance < ratio * n.distance]
    src = np.float32([k1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([k2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    return good, src, dst


def _sane(H: np.ndarray, ref_size: tuple[int, int]) -> bool:
    w, h = ref_size
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    q = cv2.perspectiveTransform(corners, H).reshape(4, 2)
    if not np.isfinite(q).all() or not cv2.isContourConvex(q.astype(np.float32)):
        return False
    ratio = abs(cv2.contourArea(q.astype(np.float32))) / (w * h)
    return 0.05 < ratio < 20


def _fit(src, dst, min_inliers: int):
    if len(src) >= 4:
        H, m = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
        if H is not None and int(m.sum()) >= min_inliers:
            return H, int(m.sum()), "homography"
    if len(src) >= 3:
        A, m = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=4.0)
        if A is not None and int(m.sum()) >= min_inliers:
            return np.vstack([A, [0, 0, 1]]), int(m.sum()), "similarity"
    return None


def rectify(scan: np.ndarray, alignment: Alignment) -> np.ndarray:
    """Warp the scan into the reference frame so template boxes apply directly."""
    w, h = alignment.ref_size
    return cv2.warpPerspective(
        scan, alignment.H, (w, h), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255),
    )


def warp_boxes(boxes: Sequence[Sequence[float]], alignment: Alignment) -> list[np.ndarray]:
    """Normalized ``[y1,x1,y2,x2]`` boxes -> 4x2 quads (TL,TR,BR,BL) in *scan* pixels."""
    w, h = alignment.ref_size
    out = []
    for y1, x1, y2, x2 in boxes:
        pts = np.float32([[x1 * w, y1 * h], [x2 * w, y1 * h], [x2 * w, y2 * h], [x1 * w, y2 * h]]).reshape(-1, 1, 2)
        out.append(cv2.perspectiveTransform(pts, alignment.H).reshape(4, 2))
    return out


def _anchor_scores(reference: np.ndarray, rectified: np.ndarray, template: Template) -> dict[str, float]:
    rg, sg = _gray(reference), _gray(rectified)
    h, w = rg.shape
    scores = {}
    for a in template.anchors:
        x1, y1, x2, y2 = norm_to_px(a.box, w, h)
        r, s = rg[y1:y2, x1:x2], sg[y1:y2, x1:x2]
        if r.size == 0 or r.std() < 1e-3 or s.std() < 1e-3:
            scores[a.id] = 0.0
            continue
        # allow a couple of pixels of residual misalignment
        pad = 3
        sp = cv2.copyMakeBorder(s, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
        v = cv2.matchTemplate(sp, r, cv2.TM_CCOEFF_NORMED).max()
        scores[a.id] = float(np.clip(v, 0.0, 1.0)) if np.isfinite(v) else 0.0
    return scores


def estimate_transform(reference: np.ndarray, scan: np.ndarray, template: Template, *, min_inliers: int = 8) -> Alignment:
    """Estimate the reference->scan transform from the template anchors. Raises AlignmentError."""
    rh, rw = reference.shape[:2]
    ref_g, rs = _downscale(_gray(reference))
    scan_g, ss = _downscale(_gray(scan))

    result = None
    for anchors_only in (True, False):
        mask = _anchor_mask(ref_g.shape, template) if anchors_only else None
        good, src, dst = _match(ref_g, scan_g, mask)
        fit = _fit(src, dst, min_inliers) if len(good) else None
        if fit is None:
            continue
        H_small, inl, method = fit
        # downscaled-ref px -> downscaled-scan px  ==>  full ref px -> full scan px
        H = np.diag([1 / ss, 1 / ss, 1.0]) @ H_small @ np.diag([rs, rs, 1.0])
        if not _sane(H, (rw, rh)):
            continue
        result = (H, inl, len(good), method, anchors_only)
        break
    if result is None:
        raise AlignmentError("could not locate template anchors in the scan (too few matching features)")

    H, inl, n, method, anchors_only = result
    al = Alignment(H=H, ref_size=(rw, rh), method=method, matches=n, inliers=inl, used_anchors_only=anchors_only)
    al.anchor_scores = _anchor_scores(reference, rectify(scan, al), template)
    feat = min(1.0, inl / 30.0) * (inl / max(n, 1)) ** 0.5
    anc = float(np.mean(list(al.anchor_scores.values()))) if al.anchor_scores else 0.0
    al.confidence = float(np.clip(0.5 * feat + 0.5 * anc, 0.0, 1.0))
    return al
