"""Filesystem storage. Layout:
data/samples/{sample_id}.png
data/templates/{template_id}/v{n}.json  +  v{n}.reference.png
"""
from __future__ import annotations

import json
import re
import shutil

from .config import data_dir

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SAMPLE = re.compile(r"^[0-9a-f]{32}$")


def safe_template_id(tid: str) -> str:
    if not _ID.match(tid) or ".." in tid:
        raise ValueError("invalid template_id")
    return tid


def sample_path(sample_id: str):
    if not _SAMPLE.match(sample_id):
        raise ValueError("invalid sample_id")
    d = data_dir() / "samples"
    d.mkdir(exist_ok=True)
    return d / f"{sample_id}.png"


def _tdir(tid: str):
    return data_dir() / "templates" / safe_template_id(tid)


def list_versions(tid: str) -> list[int]:
    d = _tdir(tid)
    if not d.exists():
        return []
    return sorted(int(m.group(1)) for p in d.glob("v*.json") if (m := re.fullmatch(r"v(\d+)\.json", p.name)))


def list_template_ids() -> list[str]:
    d = data_dir() / "templates"
    return sorted(p.name for p in d.iterdir() if p.is_dir()) if d.exists() else []


def save_template(tpl: dict, sample_id: str) -> None:
    d = _tdir(tpl["template_id"])
    d.mkdir(parents=True, exist_ok=True)
    v = tpl["version"]
    target = d / f"v{v}.json"
    if target.exists():
        raise FileExistsError(f"{tpl['template_id']} v{v} already exists")  # versions are immutable
    shutil.copyfile(sample_path(sample_id), d / f"v{v}.reference.png")
    target.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")


def load_template(tid: str, version: int) -> dict:
    return json.loads((_tdir(tid) / f"v{version}.json").read_text("utf-8"))


def reference_path(tid: str, version: int):
    return _tdir(tid) / f"v{version}.reference.png"
