import copy

import pytest

from ocrlib.schema.models import TemplateValidationError, validate_template


def make(**over):
    t = {
        "template_id": "invoice-acme",
        "version": 1,
        "status": "draft",
        "page_size": {"width_px": 1654, "height_px": 2339},
        "fingerprint": ["INVOICE", "Acme Co."],
        "anchors": [
            {"id": "a1", "text": "INVOICE", "kind": "title", "box": [0.02, 0.3, 0.06, 0.7]},
            {"id": "a2", "text": "Acme Co.", "kind": "logo", "box": [0.02, 0.05, 0.08, 0.2]},
        ],
        "fields": [
            {"key": "invoice_no", "type": "text", "box": [0.1, 0.6, 0.13, 0.9], "validator": r"^INV-\d+$"},
            {"key": "tax_id", "type": "thai_id", "box": [0.15, 0.6, 0.18, 0.9]},
            {
                "key": "items",
                "type": "table",
                "box": [0.3, 0.05, 0.7, 0.95],
                "columns": [{"key": "desc", "x1": 0.05, "x2": 0.6}, {"key": "amount", "x1": 0.6, "x2": 0.95}],
            },
        ],
    }
    t.update(over)
    return t


def test_valid_template_passes():
    t = validate_template(make())
    assert t.version == 1 and len(t.fields) == 3


def test_versions_coexist_as_distinct_documents():
    v1, v2 = validate_template(make()), validate_template(make(version=2, status="active"))
    assert (v1.template_id, v1.version) != (v2.template_id, v2.version)
    assert v1.template_id == v2.template_id


@pytest.mark.parametrize(
    "mutate,needle",
    [
        (lambda t: t["fields"][0].update(box=[0.1, 0.6, 0.13, 1.2]), "box"),
        (lambda t: t["fields"][0].update(box=[0.2, 0.6, 0.1, 0.9]), "y1<y2"),
        (lambda t: t["fields"][0].update(box=[0.1, 0.9, 0.13, 0.6]), "x1<x2"),
        (lambda t: t["fields"][0].update(box=[0.1, 0.6, 0.13]), "box"),
        (lambda t: t["fields"][0].update(type="signature"), "type"),
        (lambda t: t["fields"][0].update(validator="(unclosed"), "regex"),
        (lambda t: t["fields"][1].update(key="invoice_no"), "duplicate field keys"),
        (lambda t: t["fields"][2].pop("columns"), "columns"),
        (lambda t: t["fields"][0].update(columns=[{"key": "a", "x1": 0.1, "x2": 0.2}]), "columns"),
        (lambda t: t["fields"][2]["columns"].append({"key": "desc", "x1": 0.1, "x2": 0.2}), "duplicate column"),
        (lambda t: t["fields"][2]["columns"][0].update(x1=0.0), "outside the table box"),
        (lambda t: t.update(anchors=t["anchors"][:1]), "anchors"),
        (lambda t: t.update(anchors=t["anchors"] * 3), "anchors"),
        (lambda t: t.update(version=0), "version"),
        (lambda t: t.update(status="live"), "status"),
        (lambda t: t.pop("fingerprint"), "fingerprint"),
        (lambda t: t.update(extra=1), "extra"),
        (lambda t: t.update(template_id="bad id!"), "template_id"),
    ],
)
def test_invalid_templates_rejected(mutate, needle):
    t = copy.deepcopy(make())
    mutate(t)
    with pytest.raises(TemplateValidationError) as e:
        validate_template(t)
    assert needle in str(e.value)
