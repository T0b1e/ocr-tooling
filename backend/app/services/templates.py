"""Template use-cases: validate, version and persist drafts."""
import cv2
import numpy as np

from ocrlib.schema.models import TemplateValidationError, validate_template

from ..errors import Invalid
from ..storage import Storage, check_template_id


class TemplateService:
    def __init__(self, storage: Storage):
        self.storage = storage

    def next_version(self, template_id: str) -> int:
        return max(self.storage.list_versions(check_template_id(template_id)), default=0) + 1

    def list_all(self) -> list[dict]:
        return [
            {"template_id": tid, "versions": [
                {"version": v, "status": self.storage.load_template(tid, v)["status"]}
                for v in self.storage.list_versions(tid)]}
            for tid in self.storage.list_template_ids()
        ]

    def get(self, template_id: str, version: int) -> dict:
        return self.storage.load_template(template_id, version)

    def reference(self, template_id: str, version: int) -> bytes:
        return self.storage.read_reference(template_id, version)

    def save_draft(self, sample_id: str, template_id: str, fingerprint: list[str],
                   anchors: list[dict], fields: list[dict]) -> dict:
        """Validate and store as a new immutable `draft` version. The server assigns the version."""
        version = self.next_version(template_id)
        png = self.storage.read_sample(sample_id)
        h, w = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR).shape[:2]
        data = {
            "template_id": template_id, "version": version, "status": "draft",
            "page_size": {"width_px": w, "height_px": h},
            "fingerprint": fingerprint, "anchors": anchors, "fields": fields,
        }
        try:
            tpl = validate_template(data)
        except TemplateValidationError as e:
            raise Invalid(*e.errors) from e
        out = tpl.model_dump(mode="json", exclude_none=True)
        self.storage.save_template(out, png)
        return out
