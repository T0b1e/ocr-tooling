# TODO

## Decisions needed
- [ ] OCR engine for field crops (default Tesseract `tha+eng`; Thai accuracy is the risk)
- [ ] Confirm stack assumptions: FastAPI + React/Vite + filesystem/SQLite storage
- [ ] Are the existing services Python (import `ocrlib`) or should `extract` be exposed over HTTP?
- [ ] Is a redirect enough on completion, or do you also want a `callback_url` webhook?

## Milestone 3: alignment + extract (done)
- [x] Synthetic sample document generator + distortions (tests/synth.py)
- [x] Anchor locating (SIFT on anchor regions, whole-page retry) + RANSAC homography, similarity fallback
- [x] Rectify scan into reference frame, warp boxes to quads
- [x] `OcrEngine` protocol + `TesseractOcr` adapter
- [x] Validators/normalizers (thai_id checksum, date incl. Buddhist year, number)
- [x] `extract()` / `extract_detailed()` with per-field confidence
- [x] Tests: shifted, scaled, rotated, perspective, blurred/noisy copies
- [ ] Install Tesseract (+ tha data) and run a real-OCR smoke test on a Thai sample
- [ ] Thai month names in dates (e.g. "5 มี.ค. 2567")
- [ ] Table header-row handling (currently the table box must exclude the header)

## Milestone 4: Gemini endpoint
- [ ] PDF -> image (PyMuPDF)
- [ ] Prompt + response schema
- [ ] Rate limiter, queue, daily cost cap, hash cache, backoff retry
- [ ] Error states, key redaction in logs
- [ ] Mocked-client tests

## Milestone 5: UI
- [x] 5a canvas, manual drawing, field editor, table columns, JSON preview, save draft
- [ ] 5a follow-ups: click through the UI in a real browser; show a true diff vs previous version; edit/open an existing template; touch support check; anchor text via OCR instead of typing
- [ ] 5b Gemini detect button, checklist modal, merge, fallback to manual
- [ ] 5c `/onboard` params, sessions API, return redirect, allowlist tests

## Milestone 6-8
- [ ] Validation run + activation
- [ ] Router stub
- [ ] README: end-to-end walkthrough, env vars, `extract()` usage

## Deployment (after milestone 6)
- [ ] Decide target: internal Docker host / Kubernetes / cloud VM
- [ ] `backend/Dockerfile` with Tesseract + Thai data
- [ ] Frontend static build + serving
- [ ] `docker-compose.yml` with a persistent `DATA_DIR` volume
- [ ] `/healthz`, `.env.example`, CI (tests + image build)

## Done
- [x] Repo init, `.gitignore`
- [x] Template JSON Schema + pydantic validation + tests
- [x] Coordinate conversion + tests
- [x] README, ROADMAP, TODO
