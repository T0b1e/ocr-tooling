"""Composition root: the only place that wires adapters into services."""
from fastapi import Depends

from .config import MAX_UPLOAD_BYTES, PDF_DPI, data_dir
from .services.samples import SampleService
from .services.templates import TemplateService
from .storage import FilesystemStorage, Storage


def get_storage() -> Storage:
    return FilesystemStorage(data_dir())  # resolved per request so tests can point DATA_DIR at a temp dir


def get_sample_service(storage: Storage = Depends(get_storage)) -> SampleService:
    return SampleService(storage, MAX_UPLOAD_BYTES, PDF_DPI)


def get_template_service(storage: Storage = Depends(get_storage)) -> TemplateService:
    return TemplateService(storage)
