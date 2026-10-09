from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from ..config import MAX_UPLOAD_BYTES
from ..deps import get_sample_service
from ..schemas import SampleOut
from ..services.samples import SampleService

router = APIRouter(prefix="/api/samples", tags=["samples"])


@router.post("")
async def upload_sample(file: UploadFile = File(...), svc: SampleService = Depends(get_sample_service)) -> SampleOut:
    s = svc.ingest(await file.read(MAX_UPLOAD_BYTES + 1))
    return SampleOut(sample_id=s.sample_id, width=s.width, height=s.height, image_url=f"/api/samples/{s.sample_id}/image")


@router.get("/{sample_id}/image")
def sample_image(sample_id: str, svc: SampleService = Depends(get_sample_service)):
    return Response(svc.image(sample_id), media_type="image/png")
