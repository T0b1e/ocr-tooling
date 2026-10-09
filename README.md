# ocr-tooling

## Why this exists

We are working on a digital transformation that depends heavily on OCR. A common approach is to send every document to an LLM such as Gemini or Claude and let it read the fields. That works, but it burns a large number of tokens on every single document, and the cost adds up quickly at volume.

Most of our documents do not need that. Many document types have fields in the same place every time, and the layout has never changed. For those, **template recognition** is far cheaper and faster: we save the field positions once, then crop and read just those regions on every later document, with no LLM call.

The gap is the case where we do not have a template yet. A new document type arrives, and there is no good way to create one. This tool closes that gap. The LLM is used **once per new document type** to propose the field locations (or you draw them by hand), a person reviews them, and the result is saved as a template. After that, the OCR microservices use the saved template and never call the LLM for that document type again.

In short: **spend LLM tokens once to onboard a document type, then extract every later document with the template.**

---

Template onboarding tool for new document types. Our OCR microservices extract fields from saved per-document-type template positions; this tool creates those templates.

> Status: early development. See [ROADMAP.md](ROADMAP.md) for what exists and [TODO.md](TODO.md) for the task list.

## How it works

1. Upload a sample page (image or PDF) of a new document type.
2. Pick a mode, both of which end in the same review canvas:
   - **Gemini-assisted**: Gemini detects every field and returns boxes.
   - **Manual**: draw rectangles on the canvas yourself.
3. Review: toggle, move, resize, rename, set type, add validators, mark tables and columns.
4. Confirm: the template is saved as a versioned JSON (`draft`).
5. Validate on 3–5 more samples; when it passes, the template becomes `active`.
6. Services call `extract(image, template)` at runtime.

Other services can send users here and get them back: `/onboard?doc_type=...&return_url=...&state=...` (see *Redirect integration* below).

## Layout

```
packages/ocrlib/   shared library: schema, coordinates, alignment, extract (pip-installable)
backend/           FastAPI service: sample upload (image/PDF), template save/list/get
  app/routes/        thin HTTP handlers (parse request, call a service, shape response)
  app/services/      use-cases (SampleService, TemplateService); no HTTP, no file paths
  app/storage.py     `Storage` protocol + filesystem adapter (swap for S3/Postgres here)
  app/errors.py      domain errors, mapped to HTTP status in main.py
  app/deps.py        composition root wiring adapters into services
frontend/          React + Vite review UI: manual drawing canvas (Gemini mode coming)
data/              templates, samples, cache (gitignored)
```

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows (Git Bash); use .venv/bin/activate on Linux/macOS
pip install -e "packages/ocrlib[dev]"
cd packages/ocrlib && python -m pytest
```

## Run the app (manual drawing mode)

```powershell
# one-time
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -e "packages/ocrlib[dev]" -e "backend[dev]"
cd frontend ; npm install ; cd ..

.\dev.ps1          # opens backend on :8000 and frontend on :5173
```

Open http://127.0.0.1:5173, upload a sample, drag rectangles on the page, set key/type for fields, mark 2-4 boxes as anchors, then *Review & save draft*. Templates are written to `data/templates/{template_id}/v{n}.json` (plus the reference image).

Tests: `cd packages/ocrlib && python -m pytest`, `cd backend && python -m pytest`, `cd frontend && npm test`.

## Environment variables (planned unless noted)

Implemented now: `DATA_DIR`, `MAX_UPLOAD_MB` (20), `PDF_DPI` (200), `CORS_ORIGINS`.


| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Gemini API key. Never logged. |
| `GEMINI_MODEL` | Model name (configurable). |
| `GEMINI_DAILY_COST_CAP_USD` | Hard daily spend limit. |
| `GEMINI_RATE_LIMIT_PER_MIN` | Request rate limit. |
| `ALLOWED_RETURN_ORIGINS` | Comma-separated origins allowed as `return_url`. |
| `DATA_DIR` | Where templates, samples, cache live. |

## Template format

Coordinates are normalized 0–1 relative to page size, box order `[y1, x1, y2, x2]`. Gemini's `box_2d` (`[ymin, xmin, ymax, xmax]`, 0–1000) is converted in exactly one place: `ocrlib/coords.py`.

Top-level keys: `template_id`, `version`, `status` (`draft|active|archived`), `page_size`, `fingerprint`, `anchors[]` (2–4), `fields[]`. Field types: `text|date|number|thai_id|table|checkbox`; tables carry `columns[]`. Different versions of the same `template_id` coexist. Schema: [template.schema.json](packages/ocrlib/ocrlib/schema/template.schema.json).

```python
from ocrlib.schema.models import validate_template
template = validate_template(json_dict)   # raises TemplateValidationError
```

## Onboarding a new doc type end to end

1. Open the UI, upload a sample page. 2. Draw boxes, name fields, mark anchors (and tables with columns). 3. Review & save: a new immutable `draft` version is written. (Validation on extra samples and Gemini detection are still to come.)

## Redirect integration

*Planned (milestone 5c).* A service links the user to `/onboard` with `doc_type`, `return_url`, `origin`, `state`. After the flow, the user is redirected back to `return_url` with `status`, `template_id`, `version`, `state`. `return_url` must match `ALLOWED_RETURN_ORIGINS`.

## Calling extract from a service

```python
from ocrlib.extract import extract
from ocrlib.ocr import TesseractOcr          # pip install -e "packages/ocrlib[ocr]" + tesseract binary with tha+eng

result = extract(scan, template, reference_image, TesseractOcr())
# {"invoice_no": {"value": "INV-20431", "confidence": 0.93, "valid": True}, ...}
```

- `reference_image` is the sample page the template was built from; it is stored with each template version and is needed for feature matching. (The brief's `extract(image, template)` gained this argument and an `ocr` engine.)
- `extract_detailed()` also returns the alignment (transform, inliers, per-anchor scores). Raises `AlignmentError` when the anchors cannot be found; callers should route that to onboarding or manual review.
- Field `confidence` = OCR confidence, capped by alignment confidence and halved when a field's regex validator fails.
- Tables: the table box must exclude the header row; rows are detected by line gaps, cells by the template columns.
- Plug any OCR by implementing `read(image) -> OcrResult(text, confidence)`.
