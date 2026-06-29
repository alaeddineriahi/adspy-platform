"""
Official Meta Ad Library ingestion (Graph API `ads_archive`).

Replaces the Bright Data scraper. Pulls ads straight from Meta's public
Ad Library and indexes them into Elasticsearch so they're searchable.

Docs: https://www.facebook.com/ads/library/api/

NOTE — this raw `ads_archive` path is a DEAD END for MENA commercial ads.
Per Meta's policy it only exposes political/issue ads worldwide + all ad types
for UK/EU. With our token it returns error_subcode 2332002 for every
country/version/ad_type (incl. Germany). Real MENA commercial ads come from the
authorized Ad Library search instead — see backend/seed_real.py. This module is
kept for the EU/political use case and as the shape for future self-serve ingest.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.core.elasticsearch import get_es_client, setup_index

logger = logging.getLogger("adspy.meta")

MENA_COUNTRIES = ["TN", "DZ", "MA", "EG", "SA", "AE", "KW", "QA", "BH", "OM", "JO", "LB"]

# Fields we request from the Ad Library API.
AD_FIELDS = ",".join([
    "id",
    "page_id",
    "page_name",
    "ad_creative_bodies",
    "ad_creative_link_captions",
    "ad_creative_link_titles",
    "ad_creative_link_descriptions",
    "ad_delivery_start_time",
    "ad_delivery_stop_time",
    "ad_snapshot_url",
    "publisher_platforms",
    "languages",
])


def _graph_url() -> str:
    version = getattr(settings, "META_API_VERSION", "v21.0")
    return f"https://graph.facebook.com/{version}/ads_archive"


def _days_running(start: Optional[str], stop: Optional[str]) -> int:
    if not start:
        return 0
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = (
            datetime.fromisoformat(stop.replace("Z", "+00:00"))
            if stop
            else datetime.now(timezone.utc)
        )
        return max(0, (end_dt - start_dt).days)
    except Exception:  # noqa: BLE001
        return 0


def _platform_format(publisher_platforms: list) -> str:
    # Ad Library doesn't expose creative type reliably; default to image.
    return "image"


def map_ad(raw: dict, country: str) -> dict:
    """Map a raw Ad Library record into our Elasticsearch document schema."""
    bodies = raw.get("ad_creative_bodies") or []
    titles = raw.get("ad_creative_link_titles") or []
    captions = raw.get("ad_creative_link_captions") or []
    languages = raw.get("languages") or []
    start = raw.get("ad_delivery_start_time")
    stop = raw.get("ad_delivery_stop_time")

    return {
        "ad_id": str(raw.get("id")),
        "platform": "meta",
        "advertiser_name": raw.get("page_name") or "Unknown",
        "advertiser_id": str(raw.get("page_id") or ""),
        "country": country,
        "language": (languages[0] if languages else "en"),
        "ad_format": _platform_format(raw.get("publisher_platforms") or []),
        "copy_text": "\n\n".join(bodies),
        "cta_text": (titles[0] if titles else ""),
        "landing_page": (captions[0] if captions else raw.get("ad_snapshot_url", "")),
        "media_urls": [],  # Ad Library only exposes ad_snapshot_url (an HTML page)
        "snapshot_url": raw.get("ad_snapshot_url", ""),
        "first_seen": start or datetime.now(timezone.utc).isoformat(),
        "last_seen": stop or datetime.now(timezone.utc).isoformat(),
        "is_active": stop is None,
        "days_running": _days_running(start, stop),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_ads(
    country: str = "TN",
    search_terms: str = "",
    limit: int = 50,
    ad_active_status: str = "ALL",
    ad_type: str = "ALL",
) -> list[dict]:
    """Fetch raw ads from the Meta Ad Library for one country."""
    token = getattr(settings, "META_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("META_ACCESS_TOKEN is not configured")

    params = {
        "access_token": token,
        "ad_reached_countries": f'["{country}"]',
        "ad_active_status": ad_active_status,
        "ad_type": ad_type,
        "fields": AD_FIELDS,
        "limit": min(limit, 100),
    }
    if search_terms:
        params["search_terms"] = search_terms

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(_graph_url(), params=params)
        if resp.status_code != 200:
            # Surface Meta's error message to the caller.
            try:
                err = resp.json().get("error", {})
                msg = err.get("message", resp.text)
            except Exception:  # noqa: BLE001
                msg = resp.text
            raise RuntimeError(f"Meta API error ({resp.status_code}): {msg}")
        return resp.json().get("data", [])


async def ingest(
    country: str = "TN",
    search_terms: str = "",
    limit: int = 50,
    ad_active_status: str = "ALL",
    ad_type: str = "ALL",
) -> dict:
    """Fetch ads from Meta and index them into Elasticsearch."""
    raw_ads = await fetch_ads(
        country=country,
        search_terms=search_terms,
        limit=limit,
        ad_active_status=ad_active_status,
        ad_type=ad_type,
    )

    es = get_es_client()
    indexed = 0
    try:
        await setup_index(es)
        for raw in raw_ads:
            doc = map_ad(raw, country)
            if not doc["ad_id"]:
                continue
            await es.index(index="ads", id=doc["ad_id"], document=doc)
            indexed += 1
        await es.indices.refresh(index="ads")
    finally:
        await es.close()

    logger.info("Meta ingest: fetched=%d indexed=%d country=%s", len(raw_ads), indexed, country)
    return {"fetched": len(raw_ads), "indexed": indexed, "country": country}
