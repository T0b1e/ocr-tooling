from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import CORS_ORIGINS
from .errors import AppError, Conflict, Invalid, NotFound, TooLarge
from .routes import samples, templates

STATUS = {NotFound: 404, Conflict: 409, Invalid: 422, TooLarge: 413}

app = FastAPI(title="ocr-tooling")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(samples.router)
app.include_router(templates.router)


@app.exception_handler(AppError)
def app_error(_: Request, e: AppError):
    # same body shape the UI already parses: {"detail": {"errors": [...]}}
    return JSONResponse({"detail": {"errors": e.errors}}, status_code=STATUS[type(e)])


@app.get("/healthz")
def healthz():
    return {"ok": True}
