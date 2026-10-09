import hashlib

import cv2
import fitz  # PyMuPDF
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ocrlib.imageio import load_image

from .. import storage
from ..config import MAX_UPLOAD_BYTES, PDF_DPI

router = APIRouter(prefix="/api/samples", tags=["samples"])


def to_image(data: bytes) -> np.ndarray:
    """Image bytes or first page of a PDF -> BGR ndarray."""
    if data[:5] == b"%PDF-":
        try:
            with fitz.open(stream=data, filetype="pdf") as doc:
                if doc.page_count == 0:
                    raise ValueError("empty PDF")
                pix = doc[0].get_pixmap(dpi=PDF_DPI, alpha=False)
        except Exception as e:
            raise HTTPException(422, f"could not read PDF: {e}") from e
        arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
        return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
    try:
        return load_image(data)
    except Exception as e:
        raise HTTPException(422, "unsupported or corrupt image") from e


@router.post("")
async def upload_sample(file: UploadFile = File(...)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file too large")
    img = to_image(data)
    sample_id = hashlib.sha256(data).hexdigest()[:32]  # same file -> same id (also the future Gemini cache key)
    ok, png = cv2.imencode(".png", img)
    storage.sample_path(sample_id).write_bytes(png.tobytes())
    h, w = img.shape[:2]
    return {"sample_id": sample_id, "width": w, "height": h, "image_url": f"/api/samples/{sample_id}/image"}


@router.get("/{sample_id}/image")
def sample_image(sample_id: str):
    try:
        p = storage.sample_path(sample_id)
    except ValueError:
        raise HTTPException(404, "not found")
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="image/png")
