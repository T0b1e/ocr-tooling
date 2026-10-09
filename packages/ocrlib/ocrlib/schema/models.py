"""Pydantic models + validation for template JSON.

Two layers: the JSON Schema (structure, shared with non-Python consumers) and
pydantic cross-field checks (ordering, uniqueness, regex compile, table columns).
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from typing import Annotated, Literal

import jsonschema
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

Box = Annotated[list[float], Field(min_length=4, max_length=4)]
FieldType = Literal["text", "date", "number", "thai_id", "table", "checkbox"]


class TemplateValidationError(ValueError):
    """Raised when a template fails schema or semantic validation."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _check_box(box: list[float], where: str) -> None:
    y1, x1, y2, x2 = box
    if not all(0.0 <= v <= 1.0 for v in box):
        raise ValueError(f"{where}: box values must be within [0,1]")
    if not (y1 < y2 and x1 < x2):
        raise ValueError(f"{where}: box must satisfy y1<y2 and x1<x2 ([y1,x1,y2,x2])")


class PageSize(BaseModel):
    model_config = ConfigDict(extra="forbid")
    width_px: int = Field(ge=1)
    height_px: int = Field(ge=1)


class Anchor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    text: str
    kind: Literal["title", "logo", "label"]
    box: Box

    @model_validator(mode="after")
    def _box(self) -> "Anchor":
        _check_box(self.box, f"anchor {self.id}")
        return self


class Column(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1)
    x1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _order(self) -> "Column":
        if not self.x1 < self.x2:
            raise ValueError(f"column {self.key}: x1 must be < x2")
        return self


class Field_(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    type: FieldType
    box: Box
    validator: str | None = None
    columns: list[Column] | None = None
    source: Literal["gemini", "manual"] | None = None

    @model_validator(mode="after")
    def _semantic(self) -> "Field_":
        _check_box(self.box, f"field {self.key}")
        if self.validator is not None:
            try:
                re.compile(self.validator)
            except re.error as e:
                raise ValueError(f"field {self.key}: invalid validator regex ({e})") from e
        if self.type == "table":
            if not self.columns:
                raise ValueError(f"field {self.key}: table requires columns")
            keys = [c.key for c in self.columns]
            if len(set(keys)) != len(keys):
                raise ValueError(f"field {self.key}: duplicate column keys")
            y1, x1, y2, x2 = self.box
            for c in self.columns:
                if c.x1 < x1 - 1e-9 or c.x2 > x2 + 1e-9:
                    raise ValueError(f"field {self.key}: column {c.key} lies outside the table box")
        elif self.columns is not None:
            raise ValueError(f"field {self.key}: columns only allowed on table fields")
        return self


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    version: int = Field(ge=1)
    status: Literal["draft", "active", "archived"]
    page_size: PageSize
    fingerprint: list[str] = Field(min_length=1)
    anchors: list[Anchor] = Field(min_length=2, max_length=4)
    fields: list[Field_]

    @model_validator(mode="after")
    def _unique(self) -> "Template":
        keys = [f.key for f in self.fields]
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        if dupes:
            raise ValueError(f"duplicate field keys: {dupes}")
        ids = [a.id for a in self.anchors]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate anchor ids")
        if len(set(self.fingerprint)) != len(self.fingerprint):
            raise ValueError("duplicate fingerprint entries")
        return self


@lru_cache(maxsize=1)
def load_json_schema() -> dict:
    return json.loads(resources.files("ocrlib.schema").joinpath("template.schema.json").read_text("utf-8"))


def validate_template(data: dict) -> Template:
    """Validate against JSON Schema then pydantic. Raises TemplateValidationError."""
    validator = jsonschema.Draft202012Validator(load_json_schema())
    errors = [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path)))
    ]
    if errors:
        raise TemplateValidationError(errors)
    try:
        return Template.model_validate(data)
    except ValidationError as e:
        raise TemplateValidationError(
            [f"{'/'.join(str(p) for p in err['loc'])}: {err['msg'].removeprefix('Value error, ')}" for err in e.errors()]
        ) from e
