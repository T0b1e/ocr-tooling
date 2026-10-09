"""HTTP request/response shapes."""
from pydantic import BaseModel


class SaveTemplateRequest(BaseModel):
    sample_id: str
    template_id: str
    fingerprint: list[str]
    anchors: list[dict]
    fields: list[dict]


class SampleOut(BaseModel):
    sample_id: str
    width: int
    height: int
    image_url: str
