import pytest

from ocrlib.validators import check_pattern, normalize_date, normalize_number, normalize_thai_id


def test_thai_id_checksum():
    assert normalize_thai_id("1-1017-00230-70-8") == ("1101700230708", True)
    assert normalize_thai_id("1101700230707")[1] is False
    assert normalize_thai_id("๑๑๐๑๗๐๐๒๓๐๗๐๘") == ("1101700230708", True)
    assert normalize_thai_id("12345")[1] is False


@pytest.mark.parametrize("raw,iso,ok", [
    ("05/03/2567", "2024-03-05", True), ("5-3-2024", "2024-03-05", True),
    ("๐๕/๐๓/๒๕๖๗", "2024-03-05", True), ("31/02/2567", "31/02/2567", False), ("n/a", "n/a", False),
])
def test_date(raw, iso, ok):
    assert normalize_date(raw) == (iso, ok)


@pytest.mark.parametrize("raw,val,ok", [("1,200.50", "1200.50", True), ("๑๒๓", "123", True), ("12a", "12a", False)])
def test_number(raw, val, ok):
    assert normalize_number(raw) == (val, ok)


def test_pattern():
    assert check_pattern(None, "x") is None
    assert check_pattern(r"^A\d$", "A1") is True and check_pattern(r"^A\d$", "B1") is False
