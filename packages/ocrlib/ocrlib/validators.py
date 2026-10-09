"""Per-type value normalisation and validation of OCR text."""
from __future__ import annotations

import re
from datetime import date

_THAI_DIGITS = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")


def to_ascii_digits(s: str) -> str:
    return s.translate(_THAI_DIGITS)


def thai_id_valid(digits: str) -> bool:
    if not re.fullmatch(r"\d{13}", digits):
        return False
    total = sum(int(d) * (13 - i) for i, d in enumerate(digits[:12]))
    return (11 - total % 11) % 10 == int(digits[12])


def normalize_thai_id(text: str) -> tuple[str, bool]:
    digits = re.sub(r"\D", "", to_ascii_digits(text))
    return digits, thai_id_valid(digits)


_DATE_RE = re.compile(r"(\d{1,2})\s*[/\-.\s]\s*(\d{1,2})\s*[/\-.\s]\s*(\d{4})")


def normalize_date(text: str) -> tuple[str, bool]:
    """dd/mm/yyyy (Buddhist or Gregorian year) -> ISO yyyy-mm-dd."""
    m = _DATE_RE.search(to_ascii_digits(text))
    if not m:
        return text.strip(), False
    d, mo, y = (int(g) for g in m.groups())
    if y > 2400:
        y -= 543
    try:
        return date(y, mo, d).isoformat(), True
    except ValueError:
        return text.strip(), False


def normalize_number(text: str) -> tuple[str, bool]:
    s = to_ascii_digits(text).replace(",", "").replace(" ", "")
    return s, bool(re.fullmatch(r"-?\d+(\.\d+)?", s))


def normalize_text(text: str) -> tuple[str, bool]:
    return " ".join(text.split()), True


def check_pattern(pattern: str | None, value: str) -> bool | None:
    """None when no validator is configured, else whether the regex matches."""
    return None if not pattern else re.search(pattern, value) is not None
