# Roadmap

Build order follows dependencies. Each milestone is a small set of commits with tests.

| # | Milestone | Status |
| --- | --- | --- |
| 1 | Template schema (JSON Schema + pydantic + validation) | done |
| 2 | Coordinate conversion + tests | done |
| 3 | Alignment lib + `extract()` (anchors, homography, crop, OCR) | done (Tesseract adapter untested, binary not installed) |
| 4 | Gemini detect endpoint (limiter, queue, cost cap, cache, retry) | next |
| 5a | Review UI: canvas, manual drawing, save draft | planned |
| 5b | Review UI: Gemini overlay + checklist modal, merge, fallback to manual | planned |
| 5c | Redirect integration: `/onboard`, sessions API, return redirect, origin allowlist | planned |
| 6 | Validation run on 3–5 samples, `draft` -> `active` | planned |
| 7 | Router stub (fingerprint match + threshold -> onboarding) | planned |
| 8 | README completion (end-to-end walkthrough) | ongoing |

## Later (out of scope for v1)

- Auth / multi-tenant
- Auto-retraining
- Handwriting
- Languages beyond Thai/English
- Multi-page documents
- Server-to-server completion webhook (`callback_url`)
- Postgres/S3 storage backends behind the `Storage` interface
