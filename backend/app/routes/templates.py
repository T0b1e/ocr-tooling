from fastapi import APIRouter, Depends
from fastapi.responses import Response

from ..deps import get_template_service
from ..schemas import SaveTemplateRequest
from ..services.templates import TemplateService

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("")
def list_templates(svc: TemplateService = Depends(get_template_service)):
    return svc.list_all()


@router.get("/{template_id}/next-version")
def next_version(template_id: str, svc: TemplateService = Depends(get_template_service)):
    return {"version": svc.next_version(template_id)}


@router.get("/{template_id}/v/{version}")
def get_template(template_id: str, version: int, svc: TemplateService = Depends(get_template_service)):
    return svc.get(template_id, version)


@router.get("/{template_id}/v/{version}/reference")
def get_reference(template_id: str, version: int, svc: TemplateService = Depends(get_template_service)):
    return Response(svc.reference(template_id, version), media_type="image/png")


@router.post("", status_code=201)
def save_template(req: SaveTemplateRequest, svc: TemplateService = Depends(get_template_service)):
    return svc.save_draft(**req.model_dump())
