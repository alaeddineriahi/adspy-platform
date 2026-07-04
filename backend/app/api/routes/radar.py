"""
Trend Radar API — "what started printing money since you last looked."

Events are generated at sweep time (see app/ingestion/radar.py); this route
just reads + gates them:
  • Pro/Agency  → everything, full detail.
  • Free        → watched-brand events in full (watchlists drive engagement),
                  the first FREE_PREVIEW other events in full, and the rest
                  LOCKED: type/market/magnitude/time only, identity stripped —
                  the "3 products started scaling in TN today" FOMO teaser.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.auth import get_user_id
from app.core.credits import _active_subscription
from app.core.database import async_session
from app.models.radar import RadarEvent
from app.models.watchlist import WatchedBrand

router = APIRouter()

WINDOW_DAYS = 7
FREE_PREVIEW = 3

_LOCKED_HEADLINES = {
    "new_hot": "A new product is scaling fast",
    "momentum_flip": "A tracked product just caught fire",
    "trend_arrival": "A global winner just arrived",
    "brand_escalation": "A brand is pouring budget in right now",
    "brand_expansion": "A proven scaler launched fresh creatives",
}


def _serialize(e: RadarEvent, watched: bool) -> dict:
    return {
        "id": str(e.id),
        "event_type": e.event_type,
        "country": e.country,
        "ad_id": e.ad_id,
        "advertiser_id": e.advertiser_id,
        "advertiser_name": e.advertiser_name,
        "headline": e.headline,
        "detail": e.detail,
        "magnitude": e.magnitude,
        "heat": e.heat,
        "thumbnail": e.thumbnail,
        "created_at": e.created_at.isoformat() if e.created_at else None,
        "watched": watched,
        "locked": False,
    }


def _lock(item: dict) -> dict:
    """Strip identity, keep the FOMO: what kind of signal, where, how big, when."""
    return {
        "id": item["id"],
        "event_type": item["event_type"],
        "country": item["country"],
        "ad_id": None,
        "advertiser_id": None,
        "advertiser_name": None,
        "headline": _LOCKED_HEADLINES.get(item["event_type"], "A market signal fired"),
        "detail": None,
        "magnitude": item["magnitude"],
        "heat": item["heat"],
        "thumbnail": None,
        "created_at": item["created_at"],
        "watched": False,
        "locked": True,
    }


@router.get("")
async def get_radar(
    country: Optional[str] = Query(None, description="Scope to one market"),
    limit: int = Query(60, ge=1, le=120),
    uid: str = Depends(get_user_id),
):
    since = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    async with async_session() as db:
        plan, _bonus = await _active_subscription(db, uid)

        q = select(RadarEvent).where(RadarEvent.created_at >= since)
        if country:
            q = q.where(RadarEvent.country == country)
        rows = (await db.execute(q.order_by(RadarEvent.created_at.desc()).limit(limit))).scalars().all()

        watched_ids = {
            r[0] for r in (await db.execute(
                select(WatchedBrand.brand_id).where(WatchedBrand.user_id == uid)
            )).all()
        }

    counts: dict[str, int] = {}
    for e in rows:
        counts[e.event_type] = counts.get(e.event_type, 0) + 1

    events = [_serialize(e, e.advertiser_id in watched_ids) for e in rows]

    locked_count = 0
    if plan == "free":
        preview_left = FREE_PREVIEW
        gated = []
        for item in events:
            if item["watched"]:
                gated.append(item)
            elif preview_left > 0:
                preview_left -= 1
                gated.append(item)
            else:
                locked_count += 1
                gated.append(_lock(item))
        events = gated

    return {
        "plan": plan,
        "window_days": WINDOW_DAYS,
        "counts": {"total": len(events), **counts},
        "locked_count": locked_count,
        "events": events,
    }
