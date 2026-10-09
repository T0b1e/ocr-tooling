# ocr-tooling

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
backend/           FastAPI service (planned)
frontend/          React + Vite review UI (planned)
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

## Environment variables (planned)

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

*To be completed as the UI and backend land (milestones 4–6).*

## Redirect integration

*Planned (milestone 5c).* A service links the user to `/onboard` with `doc_type`, `return_url`, `origin`, `state`. After the flow, the user is redirected back to `return_url` with `status`, `template_id`, `version`, `state`. `return_url` must match `ALLOWED_RETURN_ORIGINS`.

## Calling extract from a service

*Planned (milestone 3).* `extract(image, template) -> {field: {value, confidence}}`.
