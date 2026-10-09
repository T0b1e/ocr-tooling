import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ocrlib.schema.models import TemplateValidationError, validate_template

from .. import storage

router = APIRouter(prefix="/api/templates", tags=["templates"])


class SaveRequest(BaseModel):
    sample_id: str
    template_id: str
    fingerprint: list[str]
    anchors: list[dict]
    fields: list[dict]


def _next_version(template_id: str) -> int:
    return max(storage.list_versions(template_id), default=0) + 1


@router.get("")
def list_templates():
    out = []
    for tid in storage.list_template_ids():
        out.append({"template_id": tid, "versions": [
            {"version": v, "status": storage.load_template(tid, v)["status"]} for v in storage.list_versions(tid)]})
    return out


@router.get("/{template_id}/next-version")
def next_version(template_id: str):
    try:
        return {"version": _next_version(template_id)}
    except ValueError:
        raise HTTPException(422, "invalid template_id")


@router.get("/{template_id}/v/{version}")
def get_template(template_id: str, version: int):
    try:
        return storage.load_template(template_id, version)
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "not found")


@router.get("/{template_id}/v/{version}/reference")
def get_reference(template_id: str, version: int):
    try:
        p = storage.reference_path(template_id, version)
    except ValueError:
        raise HTTPException(404, "not found")
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="image/png")


@router.post("", status_code=201)
def save_template(req: SaveRequest):
    """Validate and store as a new immutable `draft` version. The server assigns the version."""
    try:
        p = storage.sample_path(req.sample_id)
        version = _next_version(req.template_id)
    except ValueError as e:
        raise HTTPException(422, {"errors": [str(e)]})
    if not p.exists():
        raise HTTPException(404, {"errors": ["sample not found; upload it again"]})
    h, w = cv2.imread(str(p)).shape[:2]
    data = {
        "template_id": req.template_id, "version": version, "status": "draft",
        "page_size": {"width_px": w, "height_px": h},
        "fingerprint": req.fingerprint, "anchors": req.anchors, "fields": req.fields,
    }
    try:
        tpl = validate_template(data)
    except TemplateValidationError as e:
        raise HTTPException(422, {"errors": e.errors})
    out = tpl.model_dump(mode="json", exclude_none=True)
    try:
        storage.save_template(out, req.sample_id)
    except FileExistsError as e:
        raise HTTPException(409, {"errors": [str(e)]})
    return out
