import os
from pathlib import Path


def data_dir() -> Path:
    """Resolved per call so tests can point DATA_DIR at a temp dir."""
    p = Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parents[2] / "data")
    p.mkdir(parents=True, exist_ok=True)
    return p


MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "20")) * 1024 * 1024
PDF_DPI = int(os.environ.get("PDF_DPI", "200"))
CORS_ORIGINS = [o for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
