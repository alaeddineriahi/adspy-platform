"""
Brands API routes — brand spy: search advertisers and view their ads.
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional

from sqlalchemy import select, delete

from app.core.auth import get_user_id
from app.core.database import async_session
from app.core.elasticsearch import (
    get_es_client,
    get_brand_ads as es_brand_ads,
    get_top_brands as es_top_brands,
)
from app.models.watchlist import WatchedBrand
from app.models.brand import BrandSnapshot

router = APIRouter()


@router.get("/search")
async def search_brands(
    q: Optional[str] = Query(None, description="Filter by advertiser name (optional)"),
    country: Optional[str] = Query(None, description="ISO country code"),
    min_live_ads: int = Query(0, ge=0, description="Only brands with at least N ads live (deep-dive data)"),
    limit: int = Query(24, ge=1, le=100),
):
    """Top money-printing advertisers, ranked by total creative scaling.

    With no `q` this returns the leaderboard of brands printing the most money;
    pass `q` to filter that leaderboard by name, `min_live_ads` for the
    "brands running 50+ ads" quality cut.
    """
    es = get_es_client()
    try:
        return await es_top_brands(es, q=q, country=country, min_live_ads=min_live_ads, limit=limit)
    finally:
        await es.close()


@router.get("/{brand_id}/trajectory")
async def get_brand_trajectory(brand_id: str):
    """Deep-dive snapshot history for one brand: live-ad count over time.

    A rising series is the strongest observable "they found a winner and are
    pouring budget in" signal. Empty until the brand has been deep-dived.
    """
    async with async_session() as db:
        rows = await db.execute(
            select(BrandSnapshot.live_ads, BrandSnapshot.captured_at)
            .where(BrandSnapshot.page_id == brand_id)
            .order_by(BrandSnapshot.captured_at.asc())
            .limit(120)
        )
        points = [
            {"live_ads": n, "at": at.isoformat() if at else None}
            for n, at in rows.all()
        ]
    growth = None
    if len(points) >= 2 and points[0]["live_ads"]:
        growth = points[-1]["live_ads"] - points[0]["live_ads"]
    return {"points": points, "growth": growth}


@router.get("/{brand_id}/creatives")
async def get_brand_ads(
    brand_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all ads for a specific brand (by advertiser_id)."""
    es = get_es_client()
    try:
        return await es_brand_ads(es, advertiser_id=brand_id, page=page, limit=limit)
    finally:
        await es.close()


class WatchRequest(BaseModel):
    brand_id: str
    brand_name: Optional[str] = None


@router.post("/watchlist")
async def add_to_watchlist(req: WatchRequest, uid: str = Depends(get_user_id)):
    """Add a brand to the user's watchlist (idempotent, persisted per user)."""
    async with async_session() as db:
        exists = await db.scalar(
            select(WatchedBrand.id).where(
                WatchedBrand.user_id == uid, WatchedBrand.brand_id == req.brand_id
            )
        )
        if not exists:
            db.add(WatchedBrand(user_id=uid, brand_id=req.brand_id, brand_name=req.brand_name))
            await db.commit()
    return {"status": "added", "brand_id": req.brand_id}


@router.post("/watchlist/remove")
async def remove_from_watchlist(req: WatchRequest, uid: str = Depends(get_user_id)):
    """Remove a brand from the user's watchlist (idempotent)."""
    async with async_session() as db:
        await db.execute(
            delete(WatchedBrand).where(
                WatchedBrand.user_id == uid, WatchedBrand.brand_id == req.brand_id
            )
        )
        await db.commit()
    return {"status": "removed", "brand_id": req.brand_id}


@router.get("/watchlist")
async def get_watchlist(uid: str = Depends(get_user_id)):
    """The user's watched brands, newest first."""
    async with async_session() as db:
        rows = await db.execute(
            select(WatchedBrand.brand_id, WatchedBrand.brand_name)
            .where(WatchedBrand.user_id == uid)
            .order_by(WatchedBrand.created_at.desc())
        )
        return {"brands": [{"brand_id": b, "brand_name": n} for b, n in rows.all()]}
