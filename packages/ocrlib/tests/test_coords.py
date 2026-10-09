import pytest

from ocrlib.coords import gemini_box_to_norm, norm_to_px, px_to_norm


def test_axis_order_is_y_first_not_swapped():
    # tall-and-narrow box near the top-left: ymin=100,xmin=50,ymax=900,xmax=150
    assert gemini_box_to_norm([100, 50, 900, 150]) == [0.1, 0.05, 0.9, 0.15]


def test_full_page_and_scale():
    assert gemini_box_to_norm([0, 0, 1000, 1000]) == [0.0, 0.0, 1.0, 1.0]


def test_clamps_out_of_range():
    assert gemini_box_to_norm([-20, 10, 1040, 500]) == [0.0, 0.01, 1.0, 0.5]


def test_reordered_when_corners_reversed():
    assert gemini_box_to_norm([900, 150, 100, 50]) == [0.1, 0.05, 0.9, 0.15]


@pytest.mark.parametrize("bad", [[1, 2, 3], [1, 2, 3, 4, 5], [0, 0, float("nan"), 1], ["a", 0, 1, 1], [10, 10, 10, 50], [10, 10, 50, 10]])
def test_malformed_or_degenerate_rejected(bad):
    with pytest.raises(ValueError):
        gemini_box_to_norm(bad)


def test_norm_to_px_uses_x_first_and_nonsquare_page():
    # width 2000, height 1000; box y 0.1-0.5, x 0.25-0.75
    assert norm_to_px([0.1, 0.25, 0.5, 0.75], 2000, 1000) == (500, 100, 1500, 500)


def test_px_round_trip_nonsquare():
    w, h = 1654, 2339
    box = [0.12, 0.34, 0.56, 0.78]
    rect = norm_to_px(box, w, h)
    back = px_to_norm(rect, w, h)
    assert back == pytest.approx(box, abs=1 / min(w, h))


def test_gemini_to_px_end_to_end():
    # Gemini box over pixels x 200-600, y 100-300 on a 1000x2000 (WxH) image
    box = gemini_box_to_norm([50, 200, 150, 600])
    assert norm_to_px(box, 1000, 2000) == (200, 100, 600, 300)
