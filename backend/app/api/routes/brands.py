"""
Brands API routes — brand spy: search advertisers and view their ads.
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.core.elasticsearch import (
    get_es_client,
    get_brand_ads as es_brand_ads,
    get_top_brands as es_top_brands,
)

router = APIRouter()


@router.get("/search")
async def search_brands(
    q: Optional[str] = Query(None, description="Filter by advertiser name (optional)"),
    country: Optional[str] = Query(None, description="ISO country code"),
    limit: int = Query(24, ge=1, le=100),
):
    """Top money-printing advertisers, ranked by total creative scaling.

    With no `q` this returns the leaderboard of brands printing the most money;
    pass `q` to filter that leaderboard by name.
    """
    es = get_es_client()
    try:
        return await es_top_brands(es, q=q, country=country, limit=limit)
    finally:
        await es.close()


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


# In-memory watchlist (replace with DB-backed storage in production)
_WATCHLIST: list[str] = []


@router.post("/watchlist")
async def add_to_watchlist(brand_id: str):
    """Add a brand to the user's watchlist."""
    if brand_id not in _WATCHLIST:
        _WATCHLIST.append(brand_id)
    return {"status": "added", "watchlist": _WATCHLIST}


@router.get("/watchlist")
async def get_watchlist():
    """Get the user's watched brands."""
    return {"brands": _WATCHLIST}
