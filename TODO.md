# TODO

## Decisions needed
- [ ] OCR engine for field crops (default Tesseract `tha+eng`; Thai accuracy is the risk)
- [ ] Confirm stack assumptions: FastAPI + React/Vite + filesystem/SQLite storage
- [ ] Are the existing services Python (import `ocrlib`) or should `extract` be exposed over HTTP?
- [ ] Is a redirect enough on completion, or do you also want a `callback_url` webhook?

## Milestone 3: alignment + extract (next)
- [ ] Synthetic sample document generator for tests
- [ ] Anchor locating (feature matching, template-matching fallback)
- [ ] Transform estimation (homography, affine fallback)
- [ ] Warp field boxes, crop
- [ ] `OcrEngine` protocol + Tesseract implementation
- [ ] Validators/normalizers (thai_id checksum, date, number)
- [ ] `extract(image, template)` with per-field confidence
- [ ] Tests: shifted, scaled, rotated, perspective, blurred copies

## Milestone 4: Gemini endpoint
- [ ] PDF -> image (PyMuPDF)
- [ ] Prompt + response schema
- [ ] Rate limiter, queue, daily cost cap, hash cache, backoff retry
- [ ] Error states, key redaction in logs
- [ ] Mocked-client tests

## Milestone 5: UI
- [ ] 5a canvas, manual drawing, field editor, table columns, diff preview, save draft
- [ ] 5b Gemini detect button, checklist modal, merge, fallback to manual
- [ ] 5c `/onboard` params, sessions API, return redirect, allowlist tests

## Milestone 6-8
- [ ] Validation run + activation
- [ ] Router stub
- [ ] README: end-to-end walkthrough, env vars, `extract()` usage

## Done
- [x] Repo init, `.gitignore`
- [x] Template JSON Schema + pydantic validation + tests
- [x] Coordinate conversion + tests
- [x] README, ROADMAP, TODO
