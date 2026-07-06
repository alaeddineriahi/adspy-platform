"""
Autonomous ingestion scheduler.

When INGEST_SCHEDULE_ENABLED is true, ONE sweep covering every market — core
MENA + global trend markets — runs automatically every INGEST_INTERVAL_HOURS
hours (default 12) so the index stays fresh without anyone clicking anything.
(There used to be a separate, slower global-markets job; unified 2026-07-04 —
one feed, one sweep, one schedule. Trend markets just keep a lower per-country
cap via INGEST_GLOBAL_MAX_PER_COUNTRY.)

Safe no-op if APScheduler isn't installed or scheduling is disabled.
"""

import logging

from app.core.config import settings
from app.ingestion.pipeline import ingest_best_performing, sweep_countries
from app.ingestion.tiktok import ingest_tiktok_top_ads, tiktok_countries

logger = logging.getLogger("adspy.scheduler")

_scheduler = None


async def _run_job():
    try:
        await ingest_best_performing()  # defaults to sweep_countries(): all markets
    except Exception as e:  # noqa: BLE001 — never let a bad run kill the scheduler
        logger.exception("Scheduled ingestion failed: %s", e)


async def _run_tiktok_job():
    try:
        await ingest_tiktok_top_ads()
    except Exception as e:  # noqa: BLE001
        logger.exception("Scheduled TikTok ingestion failed: %s", e)


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
    if bool(getattr(settings, "TIKTOK_ENABLED", True)):
        tt_hours = float(getattr(settings, "TIKTOK_INTERVAL_HOURS", 24))
        _scheduler.add_job(
            _run_tiktok_job,
            trigger=IntervalTrigger(hours=tt_hours),
            id="ingest_tiktok_top_ads",
            next_run_time=None,
            max_instances=1,
            coalesce=True,
        )

    _scheduler.start()
    logger.info(
        "Ingestion scheduler started — Meta every %.1fh across %s%s.",
        hours, ",".join(sweep_countries()),
        (f"; TikTok every {float(getattr(settings, 'TIKTOK_INTERVAL_HOURS', 24)):.0f}h "
         f"across {','.join(tiktok_countries())}"
         if bool(getattr(settings, "TIKTOK_ENABLED", True)) else ""),
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
