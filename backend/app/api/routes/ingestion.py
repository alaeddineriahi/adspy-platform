"""
Self-serve ingestion API.

- POST /api/ingestion/run     -> trigger a sweep now (optionally scoped)
- GET  /api/ingestion/status  -> last run result + whether scraping is configured
- GET  /api/ingestion/config  -> current thresholds / countries / terms
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from app.core.admin_auth import require_admin
from app.core.config import settings
from app.ingestion.pipeline import (
    DEFAULT_SEARCH_TERMS,
    GLOBAL_COUNTRIES,
    LAST_RUN,
    ingest_best_performing,
    sweep_countries,
    _as_list,
)
from app.ingestion.session import session_available, describe_source, set_manual_cookie
from app.ingestion.scraper import import_search_template, has_search_template

logger = logging.getLogger("adspy.ingest.api")
# Every route needs the FB session cookie or triggers real scraping — gate
# the whole router behind admin (previously wide open to any caller).
router = APIRouter(dependencies=[Depends(require_admin)])


class CookieRequest(BaseModel):
    cookie: str


@router.post("/session")
async def save_session(req: CookieRequest):
    """Save a pasted facebook.com Cookie header (paste-once; persisted to disk)."""
    sess = await set_manual_cookie(req.cookie)
    if sess is None:
        return {"ok": False, "error": describe_source().get("error") or "invalid cookie"}
    return {"ok": True, "has_tokens": bool(sess.fb_dtsg), "user_id": sess.user_id, "source": sess.source}


class TemplateRequest(BaseModel):
    curl: str


@router.post("/search-template")
async def save_search_template(req: TemplateRequest):
    """Import the Ad Library GraphQL search request captured from the browser (Copy as cURL)."""
    tpl = import_search_template(req.curl)
    if tpl is None:
        return {"ok": False, "error": "Couldn't parse that — paste the full 'Copy as cURL' of "
                "the Ad Library graphql request (must contain doc_id and variables)."}
    return {"ok": True, "doc_id": tpl["doc_id"], "friendly_name": tpl["friendly_name"]}


class RunRequest(BaseModel):
    countries: Optional[list[str]] = None
    search_terms: Optional[list[str]] = None
    limit_per_query: int = 60
    max_per_country: Optional[int] = None
    wait: bool = False  # if true, run inline and return stats; else run in background


@router.post("/run")
async def run_ingestion(req: RunRequest, background: BackgroundTasks):
    """Trigger a best-performing ingestion sweep."""
    session_ready = await session_available()
    if req.wait:
        stats = await ingest_best_performing(
            countries=req.countries,
            search_terms=req.search_terms,
            limit_per_query=req.limit_per_query,
            max_per_country=req.max_per_country,
        )
        return {"scraping_configured": session_ready, "stats": stats}

    background.add_task(
        ingest_best_performing,
        countries=req.countries,
        search_terms=req.search_terms,
        limit_per_query=req.limit_per_query,
        max_per_country=req.max_per_country,
    )
    return {
        "started": True,
        "scraping_configured": session_ready,
        "note": (
            "Ingestion running in background; poll GET /api/ingestion/status."
            if session_ready
            else "WARNING: no Facebook session found — scrape will return 0 ads. "
                 "Log into facebook.com in your browser, or set META_FB_COOKIE. See RUNNING.md."
        ),
    }


@router.get("/status")
async def ingestion_status():
    return {
        "scraping_configured": await session_available(),
        "session": describe_source(),
        "template_captured": has_search_template(),
        "last_run": LAST_RUN,
    }


@router.get("/config")
async def ingestion_config():
    return {
        "scraping_configured": await session_available(),
        "session": describe_source(),
        "template_captured": has_search_template(),
        "schedule_enabled": bool(getattr(settings, "INGEST_SCHEDULE_ENABLED", False)),
        "interval_hours": float(getattr(settings, "INGEST_INTERVAL_HOURS", 12)),
        # ONE unified sweep: every scheduled/default run covers all of these.
        "countries": sweep_countries(),
        "search_terms": _as_list(getattr(settings, "INGEST_SEARCH_TERMS", None), DEFAULT_SEARCH_TERMS),
        "min_days_running": int(getattr(settings, "INGEST_MIN_DAYS_RUNNING", 7)),
        "min_variants": int(getattr(settings, "INGEST_MIN_VARIANTS", 3)),
        "max_per_country": int(getattr(settings, "INGEST_MAX_PER_COUNTRY", 40)),
        "global_enabled": bool(getattr(settings, "INGEST_GLOBAL_ENABLED", True)),
        "global_countries": _as_list(getattr(settings, "INGEST_GLOBAL_COUNTRIES", None), GLOBAL_COUNTRIES),
        "global_max_per_country": int(getattr(settings, "INGEST_GLOBAL_MAX_PER_COUNTRY", 60)),
    }
