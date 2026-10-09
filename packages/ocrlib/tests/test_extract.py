"""End-to-end extract() on distorted scans.

Tesseract is not required: ``LookupOcr`` recognises a crop by correlating it with crops of
known reference renders, so the test exercises alignment + cropping + normalisation exactly.
"""
import cv2
import numpy as np
import pytest

import synth
from ocrlib.align import AlignmentError
from ocrlib.extract import extract, extract_detailed
from ocrlib.ocr import OcrResult
from ocrlib.schema.models import validate_template

REF = synth.make_reference()
TPL = validate_template(synth.template_dict(REF))


def _norm(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    g = cv2.resize(g, (240, 48), interpolation=cv2.INTER_AREA).astype(np.float32)
    g -= g.mean()
    return g / (np.linalg.norm(g) + 1e-6)


class LookupOcr:
    def __init__(self, candidates: dict[str, np.ndarray]):
        self.c = {t: _norm(i) for t, i in candidates.items()}

    def read(self, image):
        q = _norm(image)
        text, score = max(((t, float((q * c).sum())) for t, c in self.c.items()), key=lambda p: p[1])
        return OcrResult(text, max(0.0, score))


def _crop(box):
    h, w = REF.shape[:2]
    y1, x1, y2, x2 = box
    return REF[int(y1 * h):int(y2 * h), int(x1 * w):int(x2 * w)]


def make_ocr():
    # candidates are padded the same way extract pads crops (white border), so scale/aspect match
    pad = lambda im: cv2.copyMakeBorder(im, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cands = {
        "INV-20431": pad(_crop(synth.F_INV)), "INV-99999": pad(synth.make_reference({"invoice_no": "INV-99999"})[
            int(synth.F_INV[0] * synth.H):int(synth.F_INV[2] * synth.H), int(synth.F_INV[1] * synth.W):int(synth.F_INV[3] * synth.W)]),
        "1101700230708": pad(_crop(synth.F_TAX)),
        "05/03/2567": pad(_crop(synth.F_DATE)),
    }
    return LookupOcr(cands)


SCANS = {
    "aligned": (synth.T(0, 0), None, {}),
    "shifted": (synth.T(70, -40), None, {}),
    "scaled": (synth.T(80, 90) @ synth.S(0.75), (1000, 1400), {}),
    "rotated": (synth.T(20, 20) @ synth.R(-4), None, {}),
    "photo": (synth.T(50, 40) @ synth.S(0.9) @ synth.R(3) @ synth.P(1.2e-5, 1e-5), (1150, 1650), {"blur": 1.0, "noise": 5}),
}


@pytest.mark.parametrize("name", SCANS)
def test_extract_values_on_distorted_scans(name):
    M, size, kw = SCANS[name]
    scan = synth.apply(REF, M, size, **kw)
    out = extract(scan, TPL, REF, make_ocr())
    assert out["invoice_no"]["value"] == "INV-20431" and out["invoice_no"]["valid"] is True
    assert out["tax_id"]["value"] == "1101700230708" and out["tax_id"]["valid"] is True  # checksum ok
    assert out["date"]["value"] == "2024-03-05" and out["date"]["valid"] is True  # BE 2567 -> 2024
    assert out["paid"]["value"] is True
    assert all(0.0 <= v["confidence"] <= 1.0 for v in out.values())


def test_unchecked_checkbox():
    scan = synth.apply(synth.make_reference(paid=False), synth.T(30, 10))
    assert extract(scan, TPL, REF, make_ocr())["paid"]["value"] is False


def test_table_rows_and_columns_from_rectified_scan():
    class CellOcr:  # returns the cell's ink bounding text via lookup of known cells
        def __init__(self):
            self.calls = 0

        def read(self, image):
            self.calls += 1
            return OcrResult("x", 0.9)

    M, size, kw = SCANS["rotated"]
    ocr = CellOcr()
    out = extract(synth.apply(REF, M, size, **kw), TPL, REF, ocr)
    rows = out["items"]["value"]
    assert len(rows) == 3
    assert set(rows[0]) == {"desc", "qty", "amount"}
    assert ocr.calls >= 9


def test_wrong_validator_value_lowers_confidence_and_flags_invalid():
    bad = synth.make_reference({"invoice_no": "INV-99999"})
    class Fixed:
        def read(self, image): return OcrResult("XX-1", 0.9)
    out = extract(bad, TPL, bad, Fixed())
    assert out["invoice_no"]["valid"] is False
    assert out["invoice_no"]["confidence"] <= 0.45 + 1e-9


def test_alignment_failure_is_explicit():
    with pytest.raises(AlignmentError):
        extract(np.full_like(REF, 255), TPL, REF, make_ocr())


def test_detailed_exposes_alignment():
    res = extract_detailed(synth.apply(REF, synth.T(10, 10)), TPL, REF, make_ocr())
    assert res.alignment.confidence > 0.6 and res.alignment.inliers >= 8
