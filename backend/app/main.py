"""FastAPI entry point.

Privacy: message text is never logged. Uvicorn's access log only records method,
path and status. Nothing is stored unless the user explicitly opts in.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import llm
from .analyzer import analyse_message
from .report import build_report

MAX_CHARS = 5000
ROOT = Path(__file__).resolve().parents[2]
OPT_IN_FILE = Path(os.environ.get("TAAKKAD_OPT_IN_FILE", ROOT / "backend" / "storage" / "opt_in.jsonl"))
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="Ta'akkad API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("TAAKKAD_CORS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api/") else response.headers.get("Cache-Control", "no-cache")
    return response


class CheckIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)
    lang: Literal["ar", "en"] = "ar"
    channel: Literal["whatsapp", "sms"] | None = None
    save_consent: bool = False  # explicit opt-in to keep the MASKED text for improving the model


class ReportIn(BaseModel):
    masked_text: str = Field(max_length=MAX_CHARS * 2)
    urls: list[str] = Field(default_factory=list, max_length=20)
    channel: Literal["whatsapp", "sms"] | None = None
    received_at: str | None = Field(default=None, max_length=40)
    what_happened: Literal["not_clicked", "clicked", "entered_card", "paid"] | None = None
    lang: Literal["ar", "en"] = "ar"


@app.get("/api/health")
def health():
    return {"ok": True, "llm_enabled": llm.enabled()}


@app.post("/api/check")
def check(body: CheckIn):
    result = analyse_message(body.text, lang=body.lang)
    result.pop("_debug_score", None)
    if body.save_consent:
        OPT_IN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with OPT_IN_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": int(time.time()), "channel": body.channel, "status": result["status"],
                                "masked_text": result["masked_text"]}, ensure_ascii=False) + "\n")
    result["saved"] = body.save_consent
    return result


@app.post("/api/report")
def report(body: ReportIn):
    # Re-mask defensively in case the client sent something unmasked.
    from .masking import mask
    return build_report(mask(body.masked_text).text, body.urls, body.channel, body.received_at, body.what_happened, body.lang)


@app.exception_handler(Exception)
async def no_leak(request: Request, exc: Exception):
    # Never echo request content back in errors.
    return JSONResponse(status_code=500, content={"error": "internal_error"})


# Serve the built frontend (npm run build) from the same origin, if present.
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        candidate = (FRONTEND_DIST / path).resolve()
        if path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
