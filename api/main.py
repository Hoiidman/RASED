"""RASED aggregate API. Set API_KEYS and ADMIN_API_KEYS before serving."""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from threading import Lock

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core import alerts, analytics, context, store, sync
from core.settings import DataUnavailable, ROOT, config

load_dotenv(ROOT / ".env")
load_dotenv(ROOT / ".env.txt")
_requests = defaultdict(deque)
_rate_lock = Lock()


def _keys(name):
    return [key.strip() for key in os.getenv(name, "").split(",") if key.strip()]


def _matches(key, candidates):
    return any(secrets.compare_digest(key, candidate) for candidate in candidates)


def authorized(x_api_key: str | None = Header(default=None)):
    if not x_api_key or not _matches(x_api_key, _keys("API_KEYS") + _keys("ADMIN_API_KEYS")):
        raise HTTPException(401, "Valid X-API-Key required")
    with _rate_lock:
        history = _requests[x_api_key]
        current = time.monotonic()
        while history and history[0] <= current - 60:
            history.popleft()
        if len(history) >= 120:
            raise HTTPException(429, "Rate limit exceeded", headers={"Retry-After": "60"})
        history.append(current)
    return x_api_key


def admin(key=Depends(authorized)):
    if not _matches(key, _keys("ADMIN_API_KEYS")):
        raise HTTPException(403, "Admin API key required")


@asynccontextmanager
async def lifespan(app):
    scheduler = None
    if os.getenv("RASED_ENABLE_SCHEDULER", "0") == "1":
        scheduler = BackgroundScheduler(timezone="UTC")
        minutes = 1 if os.getenv("RASED_DEMO_SYNC") == "1" else config("sources")["refresh_minutes"]
        scheduler.add_job(sync.run_sync, "interval", minutes=minutes, max_instances=1, coalesce=True)
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="RASED aggregate API", version="1.0.0", lifespan=lifespan)
origins = [v.strip() for v in os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",") if v.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"], allow_headers=["X-API-Key", "Content-Type"])


@app.exception_handler(DataUnavailable)
async def unavailable(request: Request, exc: DataUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def invalid(request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/v1/health", dependencies=[Depends(authorized)])
def health():
    return {"sources": sync.sync_status(), "loaded": not store.get_catalog().empty}


@app.get("/v1/indicators", dependencies=[Depends(authorized)])
def indicators():
    return store.get_catalog().to_dict("records")


@app.get("/v1/indicators/data", dependencies=[Depends(authorized)])
def data(ids: str, group: str | None = None, start: str | None = Query(None, alias="from"), end: str | None = Query(None, alias="to")):
    return store.get_series([i.strip() for i in ids.split(",")], group, start, end).to_dict("records")


@app.get("/v1/forecast/{indicator}", dependencies=[Depends(authorized)])
def forecast(indicator: str, scenario: str = Query("B", pattern="^(A|B|C|custom)$"),
             recovery_start: int = 6, recovery_len: int = 6, depth_pct: int = 100):
    rows = analytics.get_forecast(indicator, recovery_start, recovery_len, depth_pct)
    return {"method": rows.attrs.get("method"), "rows": rows.loc[rows["scenario"] == scenario].to_dict("records")}


@app.get("/v1/alerts", dependencies=[Depends(authorized)])
def alert_list(severity: str | None = None):
    return alerts.get_alerts(severity)


class Renewal(BaseModel):
    delta_pts: float = Field(ge=0, le=3)


@app.post("/v1/simulate/renewal", dependencies=[Depends(authorized)])
def renewal(body: Renewal):
    return analytics.simulate_renewal(body.delta_pts)


@app.post("/v1/sync", dependencies=[Depends(admin)])
def refresh():
    return sync.run_sync(force=True)


@app.get("/v1/changes", dependencies=[Depends(authorized)])
def changes(since: str | None = None):
    return sync.get_changes(since)


@app.get("/v1/context", dependencies=[Depends(authorized)])
def external_context(month: str, sector: str | None = None):
    return context.get_context(month, sector)


class Profile(BaseModel):
    activity: str = Field(max_length=150)
    area: str = Field(max_length=150)
    zone: str = Field(default="Mainland", pattern="^(Mainland|Free Zone)$")
    notes: str = Field(default="", max_length=2000)


@app.post("/v1/advisor", dependencies=[Depends(authorized)])
def advisor(body: Profile):
    # Keep generated advice within facts computed here; do not accept caller-supplied FACTS_JSON.
    facts = {}
    for dim, label, key in [("activity", body.activity, "sector_growth_pct"), ("zone", body.zone, "zone_change_pct")]:
        table = analytics.group_differences(dim)["table"]
        match = table.loc[table["group"] == label]
        if not match.empty:
            facts[key] = round(float(match.iloc[0]["change_pct"]), 1)
    text = "; ".join(f"{k.replace('_', ' ')}: {v:+.1f}% (H1 2026 vs H1 2025)" for k, v in facts.items())
    return {"text": (text or "No comparable data for the selected profile.") + ". Registration trends do not predict your business's performance. Indicative, not financial advice.",
            "cited_facts": list(facts), "engine": "template", "facts": facts}
