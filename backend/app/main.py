"""
AdSpy API — FastAPI application entrypoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import ads, brands, ai, users, payments, ingestion, mediabuyer, admin, radar

logger = logging.getLogger("adspy")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Best-effort startup: set up the Elasticsearch index and DB tables.
    # The API still boots if infra isn't ready yet (endpoints will report errors).
    try:
        from app.core.elasticsearch import get_es_client, setup_index

        es = get_es_client()
        try:
            await setup_index(es)
        finally:
            await es.close()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Elasticsearch not ready at startup: {e}")

    try:
        from app.core.database import init_db

        await init_db()
        logger.info("Database tables ready")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Database not ready at startup: {e}")

    # Autonomous self-serve ingestion (no-op unless INGEST_SCHEDULE_ENABLED=true).
    try:
        from app.ingestion.scheduler import start_scheduler

        start_scheduler()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Ingestion scheduler not started: {e}")

    yield

    try:
        from app.ingestion.scheduler import shutdown_scheduler

        shutdown_scheduler()
    except Exception:  # noqa: BLE001
        pass


app = FastAPI(
    title="AdSpy API",
    description="AI-powered ad intelligence platform for the MENA market.",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter added BEFORE CORS so CORS wraps it — 429 responses still carry
# CORS headers and the browser can read them instead of masking as a CORS error.
from app.core.ratelimit import RateLimitMiddleware  # noqa: E402

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: mounted at /api/creatives (NOT /api/ads) on purpose — browser ad blockers
# (uBlock/AdBlock/Brave) block any request path containing "ads", which would
# ERR_BLOCKED_BY_CLIENT every call in this ad-intelligence app.
app.include_router(ads.router, prefix="/api/creatives", tags=["creatives"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(mediabuyer.router, prefix="/api/mediabuyer", tags=["mediabuyer"])
app.include_router(users.router, prefix="/api/user", tags=["users"])
app.include_router(payments.router, prefix="/api", tags=["payments"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(radar.router, prefix="/api/radar", tags=["radar"])


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/")
async def root():
    return {"name": "AdSpy API", "docs": "/docs", "health": "/health"}
