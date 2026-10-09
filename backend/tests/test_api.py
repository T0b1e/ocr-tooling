import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    from app.main import app
    return TestClient(app)


def png_bytes(w=400, h=600):
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.putText(img, "HELLO", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    return cv2.imencode(".png", img)[1].tobytes()


def pdf_bytes():
    import fitz
    d = fitz.open()
    d.new_page(width=300, height=400).insert_text((50, 100), "Invoice")
    return d.tobytes()


def body(sample_id, **over):
    b = {
        "sample_id": sample_id, "template_id": "inv", "fingerprint": ["HELLO"],
        "anchors": [{"id": "a", "text": "HELLO", "kind": "title", "box": [0.05, 0.05, 0.15, 0.6]},
                    {"id": "b", "text": "x", "kind": "label", "box": [0.2, 0.05, 0.25, 0.3]}],
        "fields": [{"key": "no", "type": "text", "box": [0.3, 0.1, 0.35, 0.5], "source": "manual"}],
    }
    b.update(over)
    return b


def upload(client, data, name="s.png"):
    r = client.post("/api/samples", files={"file": (name, data)})
    assert r.status_code == 200, r.text
    return r.json()


def test_upload_image_and_fetch(client):
    s = upload(client, png_bytes())
    assert (s["width"], s["height"]) == (400, 600)
    r = client.get(s["image_url"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_upload_pdf_converted(client):
    s = upload(client, pdf_bytes(), "s.pdf")
    assert s["width"] > 300 and s["height"] > s["width"]  # rendered at 200 DPI


def test_upload_garbage_rejected(client):
    assert client.post("/api/samples", files={"file": ("x.png", b"not an image")}).status_code == 422


def test_save_versions_coexist_and_are_drafts(client):
    s = upload(client, png_bytes())
    r1 = client.post("/api/templates", json=body(s["sample_id"]))
    r2 = client.post("/api/templates", json=body(s["sample_id"]))
    assert (r1.status_code, r2.status_code) == (201, 201)
    assert (r1.json()["version"], r2.json()["version"]) == (1, 2)
    assert r1.json()["status"] == "draft" and r1.json()["page_size"] == {"width_px": 400, "height_px": 600}
    assert client.get("/api/templates/inv/v/1").json()["version"] == 1
    assert client.get("/api/templates/inv/v/2/reference").status_code == 200
    assert client.get("/api/templates/inv/next-version").json() == {"version": 3}
    assert client.get("/api/templates").json()[0]["versions"] == [
        {"version": 1, "status": "draft"}, {"version": 2, "status": "draft"}]


def test_invalid_template_returns_errors(client):
    s = upload(client, png_bytes())
    r = client.post("/api/templates", json=body(s["sample_id"], fields=[{"key": "n", "type": "text", "box": [0.5, 0.1, 0.2, 0.5]}]))
    assert r.status_code == 422 and "y1<y2" in str(r.json())


@pytest.mark.parametrize("tid", ["../evil", "a/b", "..", "bad id"])
def test_path_traversal_template_id_rejected(client, tid):
    s = upload(client, png_bytes())
    r = client.post("/api/templates", json=body(s["sample_id"], template_id=tid))
    assert r.status_code in (404, 422)


def test_unknown_sample(client):
    assert client.post("/api/templates", json=body("0" * 32)).status_code == 404
    assert client.get("/api/samples/zzz/image").status_code == 404
