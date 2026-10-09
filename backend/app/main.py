from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .routes import samples, templates

app = FastAPI(title="ocr-tooling")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(samples.router)
app.include_router(templates.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}
