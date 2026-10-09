import cv2
import numpy as np
import pytest

import synth
from ocrlib.align import AlignmentError, estimate_transform, rectify, warp_boxes
from ocrlib.schema.models import validate_template

REF = synth.make_reference()
TPL = validate_template(synth.template_dict(REF))
BOXES = [f.box for f in TPL.fields]

CASES = {
    "identity": (synth.T(0, 0), None, {}),
    "shift": (synth.T(60, -45), None, {}),
    "scale_down": (synth.T(100, 120) @ synth.S(0.7), (1000, 1400), {}),
    "scale_up": (synth.S(1.25), (1600, 2200), {}),
    "rotate_3": (synth.R(3), None, {}),
    "rotate_-5_shift": (synth.T(30, 25) @ synth.R(-5), None, {}),
    "perspective": (synth.T(40, 30) @ synth.P(2e-5, 1.5e-5) @ synth.R(2), None, {}),
    "photo": (synth.T(50, 40) @ synth.S(0.85) @ synth.R(-3) @ synth.P(1.5e-5, 1e-5), (1100, 1600), {"blur": 1.2, "noise": 6}),
}


def corner_error(M_true, al):
    h, w = REF.shape[:2]
    want = [cv2.perspectiveTransform(np.float32([[x, y] for x, y in
            [(b[1] * w, b[0] * h), (b[3] * w, b[0] * h), (b[3] * w, b[2] * h), (b[1] * w, b[2] * h)]]).reshape(-1, 1, 2),
            M_true).reshape(4, 2) for b in BOXES]
    got = warp_boxes(BOXES, al)
    return max(float(np.abs(a - b).max()) for a, b in zip(want, got))


@pytest.mark.parametrize("name", CASES)
def test_estimated_transform_matches_ground_truth(name):
    M, size, kw = CASES[name]
    scan = synth.apply(REF, M, size, **kw)
    al = estimate_transform(REF, scan, TPL)
    assert corner_error(M, al) < 5.0, (name, al.method, al.inliers)
    assert al.confidence > 0.6, (name, al.confidence, al.anchor_scores)


def test_rectify_restores_reference_frame():
    M, size, kw = CASES["rotate_-5_shift"]
    scan = synth.apply(REF, M, size, **kw)
    flat = rectify(scan, estimate_transform(REF, scan, TPL))
    inner = (slice(200, 1500), slice(100, 1100))  # avoid the gray border introduced by rotation
    diff = np.abs(flat[inner].astype(int) - REF[inner].astype(int)).mean()
    assert diff < 12


def test_unrelated_image_raises():
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, REF.shape, dtype=np.uint8)
    with pytest.raises(AlignmentError):
        estimate_transform(REF, noise, TPL)


def test_blank_image_raises():
    with pytest.raises(AlignmentError):
        estimate_transform(REF, np.full_like(REF, 255), TPL)
