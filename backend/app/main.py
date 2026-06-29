"""
AdSpy API — FastAPI application entrypoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import ads, brands, ai, users, payments, ingestion

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ads.router, prefix="/api/ads", tags=["ads"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(users.router, prefix="/api/user", tags=["users"])
app.include_router(payments.router, prefix="/api", tags=["payments"])


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/")
async def root():
    return {"name": "AdSpy API", "docs": "/docs", "health": "/health"}
