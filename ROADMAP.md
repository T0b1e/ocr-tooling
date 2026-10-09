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

## Deployment plan (after milestone 6)

- **Docker, not serverless.** The service needs the Tesseract binary (+ `tha` data), OpenCV, a long-lived queue/rate limiter and a persistent `DATA_DIR` (templates, samples, SQLite cache and cost ledger), which do not fit short-lived functions.
- `backend/Dockerfile`: python:3.12-slim + `tesseract-ocr tesseract-ocr-tha tesseract-ocr-eng`, installs `packages/ocrlib[ocr]`, runs uvicorn as a non-root user.
- Frontend built by Vite and served as static files, either by the backend or by nginx.
- `docker-compose.yml`: `backend` + `frontend` (or one combined image), a named volume for `DATA_DIR`, env from `.env`.
- Config via env only (`GEMINI_API_KEY`, `GEMINI_MODEL`, cost cap, `ALLOWED_RETURN_ORIGINS`, `DATA_DIR`). Secrets are never baked into the image.
- Single replica in v1 (SQLite + in-process queue). Scaling out means moving the queue, cache and ledger to Postgres/Redis and storage to S3 behind the `Storage` interface.
- Put it behind your internal reverse proxy with TLS; no public exposure while auth is out of scope. `/healthz` endpoint for the orchestrator.
- CI: pytest for `ocrlib` and `backend`, frontend build, image build.
- Services that only need `extract()` can `pip install` `ocrlib` directly instead of calling this service.
