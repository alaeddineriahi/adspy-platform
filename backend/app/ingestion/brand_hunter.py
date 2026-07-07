"""
Brand Hunter — discover winning/viral brands from LIVE signals, then pull
their full Meta catalog.

The keyword sweep + deep-dive can only dive brands our category terms happen to
surface. This adds active discovery of brands that are *proven or going viral
right now*, grounded strictly in up-to-date sources (never an LLM's stale
memory of "popular brands"):

  1. TikTok Creative Center winners — brands topping the live top-ads ranking
     we ingest. A brand going viral on TikTok almost always runs Meta ads too;
     we resolve its name → Facebook page and pull that whole catalog. This is
     genuine cross-platform discovery: "hot on TikTok this week → here's their
     entire Meta creative library."
  2. Rising scalers — brands whose live-ad count JUMPED between snapshots
     (getting viral / pouring in budget), re-dived to capture the new wave.
  3. Web research (optional) — `_web_candidate_brands()` is the seam for an
     open-web trend search; it stays empty until a search provider is
     configured, so we never inject unverified/old names.

Every candidate is a NAME or a page_id; names are resolved live against the Ad
Library (`resolve_page_id`), and the actual catalog pull reuses the sweep's
`dive_and_index_brand`, so hunted brands are scored/deduped/indexed identically.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.elasticsearch import get_es_client, setup_index
from app.models.brand import BrandSnapshot
from app.ingestion.scraper import resolve_page_id
from app.ingestion.radar import record_events

logger = logging.getLogger("adspy.hunter")

# Status surfaced by the ingestion page (mirrors the Meta/TikTok LAST_RUN shape).
HUNT_LAST_RUN: dict = {
    "status": "never_run",
    "started_at": None,
    "finished_at": None,
    "stats": None,
    "alert": None,
}


@dataclass
class BrandLead:
    """A candidate brand to hunt. Either page_id is known (rising scaler) or
    only the name is (TikTok/web) and must be resolved to a page first."""
    name: str
    country: str
    source: str                 # "tiktok_viral" | "rising_scaler" | "web_research"
    page_id: Optional[str] = None


def _enabled() -> bool:
    return bool(getattr(settings, "BRAND_HUNTER_ENABLED", True))


# Platform/house accounts that top TikTok's ranking but aren't spyable brands.
_NON_BRANDS = {
    "tiktok for business", "tiktok shop", "tiktok", "tiktok ads",
    "capcut", "meta", "facebook", "instagram",
}


def _looks_like_brand(name: str) -> bool:
    n = (name or "").strip().lower()
    if n in _NON_BRANDS or len(n) < 2:
        return False
    # A long free-text phrase (many words) is ad copy caught as a "brand", not
    # a page name — resolution would be noise. Real brand names are short.
    return len(n.split()) <= 5


async def _tiktok_viral_leads(es, limit: int) -> list[BrandLead]:
    """Named brands topping our freshly-ingested TikTok top-ads, by engagement.

    Only ads indexed in the lookback window count — the whole point is CURRENT
    virality, so stale rows never leak in."""
    lookback = int(getattr(settings, "BRAND_HUNTER_TIKTOK_LOOKBACK_DAYS", 7))
    try:
        res = await es.search(index="ads", body={
            "size": 0,
            "query": {"bool": {
                "filter": [
                    {"term": {"platform": "tiktok"}},
                    {"range": {"indexed_at": {"gte": f"now-{lookback}d"}}},
                ],
                "must_not": [
                    {"term": {"advertiser_name.keyword": "Unknown brand (TikTok)"}},
                ],
            }},
            "aggs": {"brands": {
                "terms": {"field": "advertiser_name.keyword", "size": limit,
                          "order": {"eng": "desc"}},
                "aggs": {
                    "eng": {"sum": {"field": "likes"}},
                    "country": {"terms": {"field": "country", "size": 1}},
                },
            }},
        })
    except Exception as e:  # noqa: BLE001
        logger.warning("tiktok viral-lead query failed: %s", e)
        return []
    leads = []
    for b in res.get("aggregations", {}).get("brands", {}).get("buckets", []):
        if not _looks_like_brand(b["key"]):
            continue
        cc = b["country"]["buckets"]
        leads.append(BrandLead(
            name=b["key"],
            country=cc[0]["key"] if cc else "US",
            source="tiktok_viral",
        ))
    return leads


async def _rising_scaler_leads(limit: int) -> list[BrandLead]:
    """Brands whose live-ad count grew ≥ MIN_GROWTH between their two most
    recent snapshots — proven advertisers pouring in more budget."""
    min_growth = int(getattr(settings, "BRAND_HUNTER_MIN_GROWTH", 5))
    try:
        async with async_session() as db:
            rows = (await db.execute(
                select(BrandSnapshot.page_id, BrandSnapshot.page_name,
                       BrandSnapshot.live_ads, BrandSnapshot.captured_at)
                .order_by(BrandSnapshot.captured_at.desc())
                .limit(400)
            )).all()
    except Exception as e:  # noqa: BLE001
        logger.warning("rising-scaler query failed: %s", e)
        return []
    # Keep the two latest snapshots per page, in desc-time order.
    per_page: dict[str, list] = {}
    for pid, name, live, at in rows:
        seq = per_page.setdefault(pid, [])
        if len(seq) < 2:
            seq.append((name, live or 0))
    scored = []
    for pid, seq in per_page.items():
        if len(seq) < 2:
            continue
        (name, latest), (_, prev) = seq[0], seq[1]
        growth = latest - prev
        if growth >= min_growth:
            scored.append((growth, BrandLead(name=name, country="ALL",
                                             source="rising_scaler", page_id=pid)))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [lead for _g, lead in scored[:limit]]


async def _web_candidate_brands(limit: int) -> list[BrandLead]:
    """Open-web trend research (e.g. "best-selling Shopify products this month").

    Intentionally empty until a live search provider is wired: injecting brand
    names from an LLM's training data would be exactly the stale data we must
    avoid. When a provider key is added, return fresh BrandLeads here and the
    rest of the pipeline (resolve → dive) already handles them."""
    return []


async def _recent_hunt_pages(cooldown_h: int) -> set[str]:
    """page_ids observed within the cooldown — don't re-hunt them (FB load)."""
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=cooldown_h)
        async with async_session() as db:
            rows = await db.execute(
                select(BrandSnapshot.page_id).where(BrandSnapshot.captured_at >= since)
            )
        return {r[0] for r in rows.all()}
    except Exception as e:  # noqa: BLE001
        logger.warning("hunt cooldown check failed (hunting anyway): %s", e)
        return set()


async def hunt_brands(per_run: Optional[int] = None) -> dict:
    """One discovery pass: gather live candidates → resolve → dive → index."""
    HUNT_LAST_RUN.update(
        status="running", started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, stats=None, alert=None,
    )
    try:
        stats = await _run(per_run)
        HUNT_LAST_RUN.update(status="ok", finished_at=datetime.now(timezone.utc).isoformat(),
                             stats=stats, alert=stats.pop("_alert", None))
        return stats
    except Exception as e:
        HUNT_LAST_RUN.update(status="error", finished_at=datetime.now(timezone.utc).isoformat(),
                             alert=f"Brand hunt failed: {e}")
        raise


async def _run(per_run: Optional[int]) -> dict:
    # Import here (not at module load) to avoid a pipeline<->hunter import cycle.
    from app.ingestion.pipeline import dive_and_index_brand

    per_run = per_run or int(getattr(settings, "BRAND_HUNTER_PER_RUN", 6))
    cooldown_h = int(getattr(settings, "BRAND_HUNTER_COOLDOWN_HOURS", 48))
    # Over-gather candidates: name resolution will drop the ones not on Meta.
    gather = per_run * 3

    es = get_es_client()
    try:
        await setup_index(es)
        tiktok = await _tiktok_viral_leads(es, gather)
        rising = await _rising_scaler_leads(per_run)
        web = await _web_candidate_brands(gather)

        # Order: rising scalers first (already resolved, cheap + high-signal),
        # then fresh TikTok virality, then web.
        leads = rising + tiktok + web
        recent = await _recent_hunt_pages(cooldown_h)

        radar_events: list[dict] = []
        sem = asyncio.Semaphore(8)
        stats = {
            "candidates": len(leads),
            "resolved": 0, "unresolved": 0,
            "brands_dived": 0, "catalog_indexed": 0,
            "by_source": {}, "discovered": [],
        }
        seen_pages: set[str] = set()

        for lead in leads:
            if stats["brands_dived"] >= per_run:
                break
            page_id, page_name = lead.page_id, lead.name

            # Resolve a name → page when we don't already have the id.
            if not page_id:
                resolved = await resolve_page_id(lead.name, country="ALL")
                if not resolved:
                    stats["unresolved"] += 1
                    continue
                page_id, page_name = resolved
                stats["resolved"] += 1
                await asyncio.sleep(random.uniform(1.0, 2.0))  # pace the FB session

            if page_id in seen_pages or page_id in recent:
                continue
            seen_pages.add(page_id)

            attribute_to = lead.country if lead.country and lead.country != "ALL" else "US"
            indexed, live = await dive_and_index_brand(
                es, page_id, page_name, attribute_to, sem,
                radar_events=radar_events, source=f"hunter_{lead.source}",
            )
            if indexed or live:
                stats["brands_dived"] += 1
                stats["catalog_indexed"] += indexed
                stats["by_source"][lead.source] = stats["by_source"].get(lead.source, 0) + 1
                stats["discovered"].append(
                    {"brand": page_name, "source": lead.source, "live_ads": live, "indexed": indexed}
                )
            await asyncio.sleep(random.uniform(2.0, 4.0))  # gentle on the FB session

        if stats["catalog_indexed"]:
            await es.indices.refresh(index="ads")
        stats["radar_events"] = await record_events(radar_events)
    finally:
        await es.close()

    if stats["brands_dived"] == 0:
        stats["_alert"] = (
            "Brand hunt found no new brands to dive — either no fresh TikTok "
            "leads resolved to Meta pages, or the FB session is down."
        )
    logger.info("Brand hunt done: %s", {k: stats[k] for k in
                ("candidates", "resolved", "brands_dived", "catalog_indexed")})
    return stats
