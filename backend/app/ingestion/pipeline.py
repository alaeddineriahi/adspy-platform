"""
Ingestion pipeline: scrape -> score -> filter -> dedup -> upsert.

This is the self-serve engine. It sweeps a set of MENA countries and seed search
terms, keeps only the best-performing e-commerce ads (see scoring.py), and
upserts them into the Elasticsearch `ads` index. Called both by the scheduler
(autonomous) and by the manual trigger endpoint.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Iterable, Optional

from app.core.config import settings
from app.core.elasticsearch import get_es_client, setup_index
from app.ingestion.scraper import RawAd, fetch_ads
from app.ingestion.scoring import score_ad
from app.ingestion.media import mirror_to_r2, r2_enabled

logger = logging.getLogger("adspy.ingest")

DEFAULT_COUNTRIES = ["TN", "MA", "DZ", "EG", "SA", "AE"]
# Discovery is about finding WINNING PRODUCTS, not matching discount words — and
# not the app/game/marketplace noise that a blank "browse everything" pulls in.
# So we sweep broad PRODUCT CATEGORIES across niches (FR + AR); searching a
# category structurally excludes games/apps, and the winner-scoring (longevity +
# scaling + e-commerce, global marketplaces filtered) surfaces the winners.
# Want the raw firehose? Pass "" as a search term in the UI. Want a niche? Type it.
DEFAULT_SEARCH_TERMS = [
    "cosmétique", "sérum", "crème", "parfum",   # beauty / skincare
    "montre", "lunettes", "chaussures", "sac",  # accessories / fashion
    "complément", "minceur", "cheveux",         # health / hair
    "cuisine", "gadget", "bébé",                # home / gadgets / kids
    "سيروم", "عطر", "كريم", "عناية",            # AR: serum / perfume / cream / care
]

_ARABIC_RE = re.compile(r"[؀-ۿ]")
_FRENCH_RE = re.compile(
    r"[éèàçùêâîôûÉÈÀ]|\b(le|la|les|de|des|du|pour|votre|gratuite|livraison|au|chez|et)\b",
    re.IGNORECASE,
)

# Lightweight run status, surfaced by the /status endpoint.
LAST_RUN: dict = {"status": "never_run", "started_at": None, "finished_at": None, "stats": None}


def _as_list(value, default: list[str]) -> list[str]:
    if not value:
        return default
    if isinstance(value, list):
        return value
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _detect_language(text: str, country: str) -> str:
    if _ARABIC_RE.search(text):
        return "ar"
    if _FRENCH_RE.search(text):
        return "fr"
    if country in ("TN", "MA", "DZ") and text.strip() and not text.isascii():
        return "fr"
    return "en"


def _ad_format(ad: RawAd) -> str:
    if ad.videos:
        return "video"
    if len(ad.images) > 1:
        return "carousel"
    return "image"


def _norm_key(ad: RawAd) -> str:
    """Identity used to count how many variants of one creative an advertiser runs."""
    text = re.sub(r"[^0-9a-zA-Z؀-ۿ]+", "", ad.primary_text.lower())[:60]
    return f"{ad.page_id}:{text}"


def _assign_variant_counts(ads: list[RawAd]) -> None:
    groups: dict[str, int] = {}
    for ad in ads:
        groups[_norm_key(ad)] = groups.get(_norm_key(ad), 0) + 1
    for ad in ads:
        # Keep the stronger of Meta's own collation_count and our creative grouping.
        ad.variant_count = max(ad.variant_count, groups[_norm_key(ad)])


def _to_doc(ad: RawAd, score) -> dict:
    text = ad.primary_text
    now = datetime.now(timezone.utc).isoformat()
    first_seen = (
        datetime.fromtimestamp(ad.start_ts, tz=timezone.utc).isoformat()
        if ad.start_ts else now
    )
    last_seen = (
        datetime.fromtimestamp(ad.end_ts, tz=timezone.utc).isoformat()
        if ad.end_ts else now
    )
    return {
        "ad_id": ad.ad_id,
        "platform": "meta",
        "advertiser_name": ad.page_name,
        "advertiser_id": ad.page_id,
        "country": ad.country,
        "language": _detect_language(text, ad.country),
        "ad_format": _ad_format(ad),
        "copy_text": text,
        "cta_text": ad.cta_text,
        "landing_page": ad.link_url or ad.snapshot_url,
        "media_urls": (ad.images + ad.videos),
        "snapshot_url": ad.snapshot_url,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "indexed_at": now,
        "is_active": ad.is_active,
        "days_running": score.days_running,
        "variant_count": score.variant_count,
        "performance_score": score.score,
        "is_ecommerce": score.is_ecommerce,
        "strong_commerce": score.strong_commerce,
        "ecom_signals": score.ecom_signals,
        "source": "ad_library_scrape",
    }


async def ingest_best_performing(
    countries: Optional[Iterable[str]] = None,
    search_terms: Optional[Iterable[str]] = None,
    limit_per_query: int = 60,
    max_per_country: Optional[int] = None,
) -> dict:
    """
    Run one full ingestion sweep and index the best-performing ads.

    Returns stats: {fetched, unique, kept, dropped_spam, dropped_low_perf,
    indexed, per_country, top}.
    """
    countries = list(countries) if countries else _as_list(getattr(settings, "INGEST_COUNTRIES", None), DEFAULT_COUNTRIES)
    search_terms = list(search_terms) if search_terms else _as_list(getattr(settings, "INGEST_SEARCH_TERMS", None), DEFAULT_SEARCH_TERMS)
    max_per_country = max_per_country or int(getattr(settings, "INGEST_MAX_PER_COUNTRY", 40))

    LAST_RUN.update(status="running", started_at=datetime.now(timezone.utc).isoformat(), finished_at=None)

    # 1) Scrape every (country, term). Dedup by ad_id as we go.
    by_id: dict[str, RawAd] = {}
    fetched = 0
    for country in countries:
        for term in search_terms:
            ads = await fetch_ads(country=country, search_term=term, limit=limit_per_query)
            fetched += len(ads)
            for ad in ads:
                by_id.setdefault(ad.ad_id, ad)
            await asyncio.sleep(0.5)  # gentle pacing between queries

    unique_ads = list(by_id.values())

    # 2) Scaling signal needs the full set, so count variants before scoring.
    _assign_variant_counts(unique_ads)

    # 3) Score + filter.
    now_ts = int(datetime.now(timezone.utc).timestamp())
    kept: list[tuple[RawAd, object]] = []
    dropped_spam = dropped_low_perf = 0
    for i, ad in enumerate(unique_ads):
        s = score_ad(ad, now_ts)
        if getattr(settings, "DEBUG", False) and i < 5:  # diagnostics: see why ads pass/fail
            logger.info("score: days=%s var=%s ecom=%s is_ecom=%s spam=%s keep=%s :: %s",
                        s.days_running, s.variant_count, s.ecom_signals, s.is_ecommerce,
                        s.spam_reason or "-", s.keep, ad.page_name[:30])
        if s.spam_reason:
            dropped_spam += 1
        elif not s.keep:
            dropped_low_perf += 1
        else:
            kept.append((ad, s))

    # 4) Rank by score, cap per country (keep only the very best per market).
    kept.sort(key=lambda t: t[1].score, reverse=True)
    per_country_count: dict[str, int] = {}
    final: list[tuple[RawAd, object]] = []
    for ad, s in kept:
        if per_country_count.get(ad.country, 0) >= max_per_country:
            continue
        per_country_count[ad.country] = per_country_count.get(ad.country, 0) + 1
        final.append((ad, s))

    # 5) Mirror the lead creative to R2 (persistent thumbnails), then upsert to ES.
    sem = asyncio.Semaphore(8)

    async def _build_doc(ad: RawAd, s) -> dict:
        doc = _to_doc(ad, s)
        src = ad.images[0] if ad.images else None
        if src and r2_enabled():
            async with sem:
                r2_url = await mirror_to_r2(src, f"ads/{ad.ad_id}.jpg")
            if r2_url:
                doc["media_urls"] = [r2_url] + [u for u in doc["media_urls"] if u != src]
                doc["thumbnail"] = r2_url
        elif src:
            doc["thumbnail"] = src
        return doc

    docs = await asyncio.gather(*[_build_doc(ad, s) for ad, s in final])

    indexed = 0
    es = get_es_client()
    try:
        await setup_index(es)
        for doc in docs:
            await es.index(index="ads", id=doc["ad_id"], document=doc)
            indexed += 1
        if indexed:
            await es.indices.refresh(index="ads")
    finally:
        await es.close()

    stats = {
        "fetched": fetched,
        "unique": len(unique_ads),
        "kept": len(final),
        "dropped_spam": dropped_spam,
        "dropped_low_perf": dropped_low_perf,
        "indexed": indexed,
        "per_country": per_country_count,
        "top": [
            {"advertiser": ad.page_name, "country": ad.country,
             "days_running": s.days_running, "variants": s.variant_count, "score": s.score}
            for ad, s in final[:10]
        ],
    }
    LAST_RUN.update(status="ok", finished_at=datetime.now(timezone.utc).isoformat(), stats=stats)
    logger.info("Ingestion sweep done: %s", {k: stats[k] for k in ("fetched", "unique", "kept", "indexed")})
    return stats
