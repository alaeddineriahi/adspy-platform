"""
TikTok ingestion — Creative Center "Top Ads" per market.

The Creative Center publishes the actual top-performing ads per country with
REAL engagement numbers (CTR, likes) — signals Meta never exposes. Its API
signs requests in page JS, so fetching happens in a headless browser
(tools/tiktok_topads.mjs) that intercepts the JSON the page loads for itself;
this module shells out to it, maps materials onto our ads schema, mirrors the
(expiring, signed) cover URLs to R2, and upserts into the same `ads` index so
search/filters/boards work identically across platforms.

Graceful degradation is the contract: no Node, no browser, or a TikTok block
must never break the Meta pipeline — it logs an alert and returns stats.
"""

import asyncio
import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from app.core.config import settings
from app.core.elasticsearch import get_es_client, setup_index
from app.ingestion.media import mirror_to_r2, r2_enabled
from app.ingestion.scoring import _classify_ecommerce

logger = logging.getLogger("adspy.tiktok")

_TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools"
_SCRIPT = _TOOLS_DIR / "tiktok_topads.mjs"

# Countries the Creative Center actually serves well; MENA coverage verified
# 2026-07-06 (SA 316 / EG 230 top ads; TN/MA/DZ/KW/QA are not offered).
DEFAULT_TIKTOK_COUNTRIES = ["US", "GB", "FR", "SA", "AE", "EG"]

# Status surfaced by the ingestion page, mirroring the Meta LAST_RUN shape.
TT_LAST_RUN: dict = {
    "status": "never_run",
    "started_at": None,
    "finished_at": None,
    "stats": None,
    "alert": None,
}

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def tiktok_countries() -> list[str]:
    raw = getattr(settings, "TIKTOK_COUNTRIES", None)
    if not raw:
        return DEFAULT_TIKTOK_COUNTRIES
    if isinstance(raw, list):
        return raw
    return [c.strip().upper() for c in str(raw).split(",") if c.strip()]


def _slug(name: str) -> str:
    return _SLUG_RE.sub("-", (name or "").lower()).strip("-")[:60]


def _heat_from_engagement(ctr: float, likes: int, conversion: bool) -> tuple[float, str]:
    """(heat 0-100, momentum) from the engagement TikTok actually publishes.

    CTR is the Creative Center's percentage figure (top DR ads run ~0.3–1.5);
    likes are heavy-tailed, so log-scaled against a 50k ceiling. Conversion-
    objective ads get a nudge — they're the "printing money" subset, matching
    what heat means on the Meta side.
    """
    import math
    ctr_c = min(max(ctr, 0.0), 2.0) / 2.0
    like_c = min(math.log1p(max(likes, 0)) / math.log1p(50_000), 1.0)
    heat = 100 * (0.55 * ctr_c + 0.45 * like_c)
    if conversion:
        heat *= 1.08
    heat = round(min(heat, 100.0), 1)
    momentum = "hot" if (conversion and ctr >= 0.5) else "steady"
    return heat, momentum


def _to_doc(m: dict, country: str, now: str) -> Optional[dict]:
    mid = str(m.get("id") or "").strip()
    if not mid:
        return None
    title = (m.get("ad_title") or "").strip()
    brand = (m.get("brand_name") or "").strip()
    if brand.lower() in {"not mention", "unknown"}:
        brand = ""
    objective = str(m.get("objective_key") or "")
    conversion = any(k in objective for k in ("conversion", "product", "catalog", "purchase"))

    ctr = float(m.get("ctr") or 0.0)
    likes = int(m.get("like") or 0)
    heat, momentum = _heat_from_engagement(ctr, likes, conversion)

    is_ecom, signals, strong, spam = _classify_ecommerce(title)
    if conversion:  # a conversion objective IS a hard commerce signal
        signals += 2
        is_ecom, strong = True, True

    video = m.get("video_info") or {}
    cover = video.get("cover") or ""
    video_url = (video.get("video_url") or {}).get("720p") or ""
    # The durable link — CDN URLs above are signed and expire within days.
    permalink = f"https://ads.tiktok.com/business/creativecenter/topads/{mid}/pc/en"

    return {
        "ad_id": f"tt_{mid}",
        "platform": "tiktok",
        # Unbranded materials keep a per-ad advertiser_id so Brand Spy never
        # aggregates thousands of unknowns into one fake mega-brand.
        "advertiser_name": brand or "Unknown brand (TikTok)",
        "advertiser_id": f"ttb_{_slug(brand)}" if brand else f"tt_{mid}",
        "country": country,
        "countries": [country],
        "language": _lang(title, country),
        "ad_format": "video",
        "copy_text": title,
        "cta_text": "",
        "landing_page": permalink,
        "media_urls": [u for u in (cover, video_url) if u],
        "snapshot_url": permalink,
        "first_seen": now,
        "last_seen": now,
        "indexed_at": now,
        "is_active": True,
        # Longevity is unknowable from the Creative Center — leave the field
        # absent rather than fake a 0-day age (sorts put missing last).
        "variant_count": 1,
        "performance_score": heat,
        "heat": heat,
        "velocity": 0.0,
        "momentum": momentum,
        "is_ecommerce": is_ecom,
        "strong_commerce": strong,
        "ecom_signals": signals,
        "creative_key": f"tt_{mid}",
        "source": "tiktok_top_ads",
        # TikTok-only engagement (Meta never exposes these):
        "likes": likes,
        "ctr": ctr,
        "video_duration": round(float(video.get("duration") or 0.0), 1),
        "tt_industry": str(m.get("industry_key") or ""),
        "tt_objective": objective,
    }


def _lang(text: str, country: str) -> str:
    # Local import to avoid a pipeline<->tiktok cycle at module load.
    from app.ingestion.pipeline import _detect_language
    return _detect_language(text, country)


async def _run_fetcher(countries: list[str], limit: int, period: int) -> dict:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js not found on PATH — TikTok ingestion needs it (tools/tiktok_topads.mjs).")
    if not _SCRIPT.exists():
        raise RuntimeError(f"Fetcher script missing: {_SCRIPT}")
    proc = await asyncio.create_subprocess_exec(
        node, str(_SCRIPT),
        "--countries", ",".join(countries),
        "--limit", str(limit),
        "--period", str(period),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(_TOOLS_DIR),
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=420)
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("TikTok fetcher timed out (7 min).")
    if not out.strip():
        raise RuntimeError(f"TikTok fetcher produced no output. stderr: {err.decode(errors='replace')[:300]}")
    return json.loads(out)


async def ingest_tiktok_top_ads(
    countries: Optional[Iterable[str]] = None,
    limit_per_country: Optional[int] = None,
) -> dict:
    """One TikTok sweep: fetch top ads per market, map, mirror covers, upsert."""
    countries = list(countries) if countries else tiktok_countries()
    limit = limit_per_country or int(getattr(settings, "TIKTOK_MAX_PER_COUNTRY", 40))
    period = int(getattr(settings, "TIKTOK_PERIOD_DAYS", 30))

    TT_LAST_RUN.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, stats=None, alert=None,
    )
    try:
        stats = await _sweep(countries, limit, period)
        TT_LAST_RUN.update(
            status="ok",
            finished_at=datetime.now(timezone.utc).isoformat(),
            stats=stats,
            alert=stats.pop("_alert", None),
        )
        return stats
    except Exception as e:
        TT_LAST_RUN.update(
            status="error",
            finished_at=datetime.now(timezone.utc).isoformat(),
            alert=f"TikTok sweep failed: {e}",
        )
        raise


async def _sweep(countries: list[str], limit: int, period: int) -> dict:
    data = await _run_fetcher(countries, limit, period)
    fetch_errors = data.get("errors") or []
    now = datetime.now(timezone.utc).isoformat()

    docs: list[dict] = []
    per_country: dict[str, int] = {}
    for country, materials in (data.get("countries") or {}).items():
        n = 0
        for m in materials or []:
            doc = _to_doc(m, country, now)
            if doc:
                docs.append(doc)
                n += 1
        per_country[country] = n

    # Mirror covers to R2 — the CDN URLs are signed and expire within days,
    # so skipping this means gray tiles a week from now.
    if docs and r2_enabled():
        sem = asyncio.Semaphore(8)

        async def _mirror(doc: dict) -> None:
            src = (doc.get("media_urls") or [None])[0]
            if not src:
                return
            async with sem:
                r2_url = await mirror_to_r2(src, f"media/{doc['ad_id']}.jpg")
            if r2_url:
                doc["thumbnail"] = r2_url
                doc["media_urls"] = [r2_url] + doc["media_urls"][1:]
            else:
                doc["thumbnail"] = src
        await asyncio.gather(*[_mirror(d) for d in docs])
    else:
        for d in docs:
            if d.get("media_urls"):
                d["thumbnail"] = d["media_urls"][0]

    indexed = 0
    es = get_es_client()
    try:
        await setup_index(es)
        # Same cross-market identity rule as the Meta sweep: an ad topping in
        # SA and AE keeps one doc with both countries. Local import — pipeline
        # is heavy and tiktok must stay importable without it at module load.
        from app.ingestion.pipeline import _merge_existing
        await _merge_existing(es, docs)
        for doc in docs:
            await es.index(index="ads", id=doc["ad_id"], document=doc)
            indexed += 1
        if indexed:
            await es.indices.refresh(index="ads")
    finally:
        await es.close()

    stats = {
        "fetched": sum(len(v or []) for v in (data.get("countries") or {}).values()),
        "indexed": indexed,
        "per_country": per_country,
        "fetch_errors": fetch_errors,
    }
    if fetch_errors and not indexed:
        stats["_alert"] = "TikTok fetch returned nothing — check Node/Edge on the server. " + "; ".join(fetch_errors[:3])
    logger.info("TikTok sweep done: %s", stats)
    return stats
