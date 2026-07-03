"""
Autonomous ingestion scheduler.

When INGEST_SCHEDULE_ENABLED is true, the pipeline runs automatically every
INGEST_INTERVAL_HOURS hours (default 12) so the index stays fresh without anyone
clicking anything — the "self-serve" part. Safe no-op if APScheduler isn't
installed or scheduling is disabled.
"""

import logging

from app.core.config import settings
from app.ingestion.pipeline import GLOBAL_COUNTRIES, _as_list, ingest_best_performing

logger = logging.getLogger("adspy.scheduler")

_scheduler = None


async def _run_job():
    try:
        await ingest_best_performing()
    except Exception as e:  # noqa: BLE001 — never let a bad run kill the scheduler
        logger.exception("Scheduled ingestion failed: %s", e)


async def _run_global_job():
    """Trend markets (US/CA/GB/AU/FR) — lighter cadence + lower cap; trends
    there reach MENA months later, so freshness matters less than coverage."""
    try:
        await ingest_best_performing(
            countries=_as_list(getattr(settings, "INGEST_GLOBAL_COUNTRIES", None), GLOBAL_COUNTRIES),
            max_per_country=int(getattr(settings, "INGEST_GLOBAL_MAX_PER_COUNTRY", 60)),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("Scheduled global-trends ingestion failed: %s", e)


def start_scheduler() -> None:
    global _scheduler
    if not bool(getattr(settings, "INGEST_SCHEDULE_ENABLED", False)):
        logger.info("Ingestion scheduler disabled (set INGEST_SCHEDULE_ENABLED=true to enable).")
        return
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.warning("APScheduler not installed — autonomous ingestion is off. `pip install apscheduler`.")
        return

    hours = float(getattr(settings, "INGEST_INTERVAL_HOURS", 12))
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_job,
        trigger=IntervalTrigger(hours=hours),
        id="ingest_best_performing",
        next_run_time=None,  # don't fire immediately on boot; first run after one interval
        max_instances=1,
        coalesce=True,
    )
    global_hours = float(getattr(settings, "INGEST_GLOBAL_INTERVAL_HOURS", 72))
    if bool(getattr(settings, "INGEST_GLOBAL_ENABLED", True)):
        _scheduler.add_job(
            _run_global_job,
            trigger=IntervalTrigger(hours=global_hours),
            id="ingest_global_trends",
            next_run_time=None,
            max_instances=1,
            coalesce=True,
        )
    _scheduler.start()
    logger.info(
        "Ingestion scheduler started — core every %.1fh, global trends every %.1fh.",
        hours, global_hours,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
