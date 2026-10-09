"""Sample ingestion: bytes (image or PDF) -> normalised PNG stored under a content-hash id."""
import hashlib
from dataclasses import dataclass

import cv2
import fitz  # PyMuPDF
import numpy as np

from ocrlib.imageio import load_image

from ..errors import Invalid, TooLarge
from ..storage import Storage


@dataclass(frozen=True)
class Sample:
    sample_id: str
    width: int
    height: int


def to_image(data: bytes, pdf_dpi: int) -> np.ndarray:
    """Image bytes or first page of a PDF -> BGR ndarray."""
    if data[:5] == b"%PDF-":
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.page_count == 0:
                    raise ValueError("empty PDF")
                pix = doc[0].get_pixmap(dpi=pdf_dpi, alpha=False)
        except Exception as e:
            raise Invalid(f"could not read PDF: {e}") from e
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    try:
        return load_image(data)
    except Exception as e:
        raise Invalid("unsupported or corrupt image") from e


class SampleService:
    def __init__(self, storage: Storage, max_bytes: int, pdf_dpi: int):
        self.storage, self.max_bytes, self.pdf_dpi = storage, max_bytes, pdf_dpi

    def ingest(self, data: bytes) -> Sample:
        if len(data) > self.max_bytes:
            raise TooLarge("file too large")
        img = to_image(data, self.pdf_dpi)
        sample_id = hashlib.sha256(data).hexdigest()[:32]  # same file -> same id (also the future Gemini cache key)
        self.storage.save_sample(sample_id, cv2.imencode(".png", img)[1].tobytes())
        h, w = img.shape[:2]
        return Sample(sample_id, w, h)

    def image(self, sample_id: str) -> bytes:
        return self.storage.read_sample(sample_id)
