"""Storage port and its filesystem adapter. Layout:
data/samples/{sample_id}.png
data/templates/{template_id}/v{n}.json  +  v{n}.reference.png

Services depend on the `Storage` protocol only; swap the adapter (S3, Postgres) without touching them.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Protocol

from .errors import Conflict, Invalid, NotFound

_TEMPLATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SAMPLE_ID = re.compile(r"^[0-9a-f]{32}$")


class Storage(Protocol):
    def save_sample(self, sample_id: str, png: bytes) -> None: ...
    def read_sample(self, sample_id: str) -> bytes: ...
    def list_template_ids(self) -> list[str]: ...
    def list_versions(self, template_id: str) -> list[int]: ...
    def save_template(self, tpl: dict, reference_png: bytes) -> None: ...
    def load_template(self, template_id: str, version: int) -> dict: ...
    def read_reference(self, template_id: str, version: int) -> bytes: ...


def check_template_id(tid: str) -> str:
    if not _TEMPLATE_ID.match(tid) or ".." in tid:
        raise Invalid("invalid template_id")
    return tid


def check_sample_id(sid: str) -> str:
    if not _SAMPLE_ID.match(sid):
        raise Invalid("invalid sample_id")
    return sid


class FilesystemStorage:
    def __init__(self, root: Path):
        self.root = root

    def _sample(self, sample_id: str) -> Path:
        return self.root / "samples" / f"{check_sample_id(sample_id)}.png"

    def _tdir(self, template_id: str) -> Path:
        return self.root / "templates" / check_template_id(template_id)

    def save_sample(self, sample_id: str, png: bytes) -> None:
        p = self._sample(sample_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(png)

    def read_sample(self, sample_id: str) -> bytes:
        try:
            return self._sample(sample_id).read_bytes()
        except (Invalid, FileNotFoundError):
            raise NotFound("sample not found; upload it again") from None

    def list_template_ids(self) -> list[str]:
        d = self.root / "templates"
        return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []

    def list_versions(self, template_id: str) -> list[int]:
        d = self._tdir(template_id)
        if not d.exists():
            return []
        return sorted(int(m.group(1)) for p in d.glob("v*.json") if (m := re.fullmatch(r"v(\d+)\.json", p.name)))

    def save_template(self, tpl: dict, reference_png: bytes) -> None:
        d = self._tdir(tpl["template_id"])
        d.mkdir(parents=True, exist_ok=True)
        v = tpl["version"]
        target = d / f"v{v}.json"
        if target.exists():
            raise Conflict(f"{tpl['template_id']} v{v} already exists")  # versions are immutable
        (d / f"v{v}.reference.png").write_bytes(reference_png)
        target.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_template(self, template_id: str, version: int) -> dict:
        try:
            return json.loads((self._tdir(template_id) / f"v{version}.json").read_text("utf-8"))
        except (Invalid, FileNotFoundError):
            raise NotFound("template not found") from None

    def read_reference(self, template_id: str, version: int) -> bytes:
        try:
            return (self._tdir(template_id) / f"v{version}.reference.png").read_bytes()
        except (Invalid, FileNotFoundError):
            raise NotFound("reference image not found") from None
