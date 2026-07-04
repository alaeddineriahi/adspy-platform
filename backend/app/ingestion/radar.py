"""
Trend Radar event detection — pure diffing of state the sweep already computes.

Called from the pipeline with the PRIOR state of re-seen ads (captured by
_merge_existing before the upsert overwrites it) and the freshly built docs.
Zero extra scraping, zero LLM: maximum signal per compute.

Noise control:
  • per-sweep caps per event type (a rebuilt index would otherwise flood
    hundreds of "new hot" events),
  • 7-day dedupe per (ad_id|advertiser_id, event_type),
  • 14-day retention prune.
Everything is best-effort — radar must never fail a sweep.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from app.core.database import async_session
from app.models.radar import RadarEvent

logger = logging.getLogger("adspy.radar")

RETENTION_DAYS = 14
DEDUPE_DAYS = 7
MAX_PER_TYPE_PER_SWEEP = 12


def _fmt_spend(lo) -> str:
    if not lo:
        return ""
    if lo >= 1000:
        return f", est. ${lo/1000:.0f}k+ already spent"
    return f", est. ${lo}+ already spent"


def detect_ad_events(prior: dict[str, dict], docs: list[dict], core_markets: set[str]) -> list[dict]:
    """Diff freshly built docs against their pre-upsert state → event dicts."""
    events: list[dict] = []
    new_hot: list[dict] = []

    for d in docs:
        old = prior.get(d["ad_id"])
        base = {
            "country": d.get("country"),
            "ad_id": d.get("ad_id"),
            "advertiser_id": d.get("advertiser_id"),
            "advertiser_name": d.get("advertiser_name"),
            "heat": d.get("heat"),
            "thumbnail": d.get("thumbnail"),
        }
        detail = (
            f"{d.get('variant_count', 1)} creative variants in {d.get('days_running', 0)}d"
            f"{_fmt_spend(d.get('est_spend_min_usd'))}"
        )

        if old is None:
            if d.get("momentum") == "hot":
                new_hot.append({
                    **base, "event_type": "new_hot",
                    "headline": f"{d.get('advertiser_name')} entered scaling fast",
                    "detail": detail,
                    "magnitude": d.get("variant_count"),
                })
            continue

        # steady/proven → hot: the "started printing money NOW" flip.
        if d.get("momentum") == "hot" and old.get("momentum") in ("steady", "proven"):
            events.append({
                **base, "event_type": "momentum_flip",
                "headline": f"{d.get('advertiser_name')} just caught fire",
                "detail": f"Was {old.get('momentum')}, now scaling — {detail}",
                "magnitude": d.get("variant_count"),
            })

        # Seen only in global trend markets before, now in a MENA market.
        old_countries = set(old.get("countries") or [])
        added = set(d.get("countries") or []) - old_countries
        if (
            old_countries
            and not (old_countries & core_markets)
            and (added & core_markets)
        ):
            arrived_in = sorted(added & core_markets)
            events.append({
                **base, "event_type": "trend_arrival",
                "country": arrived_in[0],
                "headline": f"Global winner just landed in {'/'.join(arrived_in)}",
                "detail": (
                    f"{d.get('advertiser_name')} was scaling in "
                    f"{'/'.join(sorted(old_countries))} — the wave is arriving. {detail}"
                ),
                "magnitude": d.get("variant_count"),
            })

    # Cap the noisiest type by heat so a big sweep surfaces the best, not the most.
    new_hot.sort(key=lambda e: e.get("heat") or 0, reverse=True)
    events.extend(new_hot[:MAX_PER_TYPE_PER_SWEEP])
    return events


def brand_escalation_event(page_id: str, page_name: str, prev_live: int, live: int) -> dict | None:
    """A deep-dived brand's live-ad count jumped meaningfully since last snapshot."""
    delta = live - prev_live
    if prev_live <= 0 or delta < max(5, int(prev_live * 0.2)):
        return None
    return {
        "event_type": "brand_escalation",
        "advertiser_id": page_id,
        "advertiser_name": page_name,
        "headline": f"{page_name} is pouring budget in",
        "detail": f"Live ads jumped {prev_live} → {live} since we last checked — "
                  "brands only scale like this on a winner.",
        "magnitude": delta,
    }


def brand_expansion_event(page_id: str, page_name: str, country: str, new_ads: int) -> dict | None:
    """A tracked brand shipped a batch of fresh winning creatives (deep-dive)."""
    if new_ads < 5:
        return None
    return {
        "event_type": "brand_expansion",
        "advertiser_id": page_id,
        "advertiser_name": page_name,
        "country": country,
        "headline": f"{page_name} launched {new_ads} new winning creatives",
        "detail": "Fresh angles from a proven scaler — prime swipe material.",
        "magnitude": new_ads,
    }


async def record_events(events: list[dict]) -> int:
    """Persist events (recent-dupe filtered) and prune old rows. Best-effort."""
    if not events:
        events = []
    try:
        async with async_session() as db:
            since = datetime.now(timezone.utc) - timedelta(days=DEDUPE_DAYS)
            rows = await db.execute(
                select(RadarEvent.ad_id, RadarEvent.advertiser_id, RadarEvent.event_type)
                .where(RadarEvent.created_at >= since)
            )
            seen = set()
            for ad_id, adv_id, etype in rows.all():
                seen.add((ad_id or adv_id, etype))

            written = 0
            per_type: dict[str, int] = {}
            for e in events:
                key = (e.get("ad_id") or e.get("advertiser_id"), e["event_type"])
                if key in seen:
                    continue
                if per_type.get(e["event_type"], 0) >= MAX_PER_TYPE_PER_SWEEP:
                    continue
                seen.add(key)
                per_type[e["event_type"]] = per_type.get(e["event_type"], 0) + 1
                db.add(RadarEvent(**e))
                written += 1

            await db.execute(
                delete(RadarEvent).where(
                    RadarEvent.created_at
                    < datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
                )
            )
            await db.commit()
            if written:
                logger.info("Radar: recorded %s events %s", written, per_type)
            return written
    except Exception as e:  # noqa: BLE001 — radar must never fail a sweep
        logger.warning("Radar event recording failed: %s", e)
        return 0
