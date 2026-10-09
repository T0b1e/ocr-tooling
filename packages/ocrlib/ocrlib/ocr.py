"""OCR engine abstraction. Plug your own engine by implementing ``read``."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class OcrResult:
    text: str
    confidence: float  # 0-1


class OcrEngine(Protocol):
    def read(self, image: np.ndarray) -> OcrResult:
        """OCR one small, already-cropped, rectified field image (BGR or gray)."""
        ...


class TesseractOcr:
    """Tesseract via pytesseract (``pip install ocrlib[ocr]`` plus the tesseract binary and tha/eng data)."""

    def __init__(self, lang: str = "tha+eng", psm: int = 7, cmd: str | None = None):
        try:
            import pytesseract
        except ImportError as e:  # pragma: no cover
            raise RuntimeError("pytesseract not installed: pip install 'ocrlib[ocr]'") from e
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        self._t, self.lang, self.psm = pytesseract, lang, psm

    def read(self, image: np.ndarray) -> OcrResult:
        d = self._t.image_to_data(
            image, lang=self.lang, config=f"--psm {self.psm}", output_type=self._t.Output.DICT
        )
        words = [(w, float(c)) for w, c in zip(d["text"], d["conf"]) if w.strip() and float(c) >= 0]
        if not words:
            return OcrResult("", 0.0)
        return OcrResult(" ".join(w for w, _ in words), sum(c for _, c in words) / len(words) / 100.0)
