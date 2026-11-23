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

import logging
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import llm, stats
from .analyzer import analyse_message
from .report import build_report

log = logging.getLogger("taakkad")

# Staff dashboard token. If not configured, a random one is generated per run and
# printed once to the server console (local demo only). Production: replace with
# the authority's own sign-in (SSO) - see README.
ADMIN_TOKEN = os.environ.get("TAAKKAD_ADMIN_TOKEN") or secrets.token_urlsafe(18)
if "TAAKKAD_ADMIN_TOKEN" not in os.environ:
    print(f"[taakkad] dashboard token for this run: {ADMIN_TOKEN}", flush=True)


def require_admin(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {ADMIN_TOKEN}"
    if not authorization or not secrets.compare_digest(authorization.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="unauthorized")

MAX_CHARS = 5000
ROOT = Path(__file__).resolve().parents[2]
OPT_IN_FILE = Path(os.environ.get("TAAKKAD_OPT_IN_FILE", ROOT / "backend" / "storage" / "opt_in.jsonl"))
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="Ta'akkad API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("TAAKKAD_CORS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
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
    try:
        stats.record_check(result, body.channel, body.lang)  # aggregate fields only, never text
    except Exception as exc:  # stats must never break a check
        log.warning("stats not recorded (%s)", type(exc).__name__)
    result = {k: v for k, v in result.items() if not k.startswith("_")}
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


@app.get("/api/alerts")
def public_alerts(lang: Literal["ar", "en"] = "ar"):
    """Warnings published by the authority, shown to the public in the app."""
    return [{"id": a["id"], "created_at": a["created_at"], "title": a[f"title_{lang}"], "body": a[f"body_{lang}"]}
            for a in stats.list_alerts(active_only=True)]


# ---- Authority dashboard (staff only) -------------------------------------

class AlertIn(BaseModel):
    title_ar: str = Field(min_length=2, max_length=120)
    title_en: str = Field(min_length=2, max_length=120)
    body_ar: str = Field(min_length=2, max_length=600)
    body_en: str = Field(min_length=2, max_length=600)


class DomainIn(BaseModel):
    domain: str = Field(min_length=3, max_length=253, pattern=r"^[a-z0-9.-]+$")


@app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
def admin_stats(days: int = 14):
    return stats.summary(days)


@app.get("/api/admin/alerts", dependencies=[Depends(require_admin)])
def admin_alerts():
    return stats.list_alerts(active_only=False)


@app.post("/api/admin/alerts", dependencies=[Depends(require_admin)])
def admin_add_alert(body: AlertIn):
    return {"id": stats.add_alert(body.title_ar, body.title_en, body.body_ar, body.body_en)}


@app.post("/api/admin/alerts/{alert_id}/active", dependencies=[Depends(require_admin)])
def admin_alert_active(alert_id: int, active: bool):
    stats.set_alert_active(alert_id, active)
    return {"ok": True}


@app.post("/api/admin/confirmed-domains", dependencies=[Depends(require_admin)])
def admin_confirm(body: DomainIn):
    from .url_checks import SHORTENERS
    from .entities import load_catalog
    if body.domain in SHORTENERS:
        # Confirming bit.ly etc. would flag every shortened link, legitimate ones included.
        raise HTTPException(status_code=400, detail="shortener_not_allowed")
    if body.domain in load_catalog().official_domains():
        raise HTTPException(status_code=400, detail="official_domain")
    stats.confirm_domain(body.domain)
    return {"ok": True}


@app.delete("/api/admin/confirmed-domains/{domain}", dependencies=[Depends(require_admin)])
def admin_unconfirm(domain: str):
    stats.unconfirm_domain(domain)
    return {"ok": True}


@app.exception_handler(HTTPException)
async def http_errors(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


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
