"""
Ads API routes — search, trending, detail.
Wired to Elasticsearch for full-text search with filters.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.core.elasticsearch import (
    get_es_client,
    search_ads as es_search,
    get_trending_ads as es_trending,
)

router = APIRouter()


@router.get("/search")
async def search_ads(
    q: Optional[str] = Query(None, description="Search query"),
    platform: Optional[str] = Query(None, description="meta or tiktok"),
    format: Optional[str] = Query(None, description="image, video, or carousel"),
    country: Optional[str] = Query(None, description="ISO country code"),
    language: Optional[str] = Query(None, description="en, ar, or fr"),
    active: Optional[bool] = Query(None, description="Active ads only"),
    momentum: Optional[str] = Query(None, description="hot, proven, or steady"),
    min_days: Optional[int] = Query(None, ge=1, le=3650, description="Min days running"),
    min_variants: Optional[int] = Query(None, ge=1, le=1000, description="Min creative variants (scaling)"),
    min_spend: Optional[int] = Query(None, ge=1, description="Min estimated spend band ceiling, USD"),
    sort: str = Query("newest", description="newest, longest_running, relevance"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Search ads with full-text query and filters."""
    es = get_es_client()
    try:
        results = await es_search(
            es=es,
            q=q or "",
            platform=platform,
            country=country,
            language=language,
            ad_format=format,
            is_active=active,
            momentum=momentum,
            min_days=min_days,
            min_variants=min_variants,
            min_spend=min_spend,
            sort=sort,
            page=page,
            limit=limit,
        )
        return results
    finally:
        await es.close()


@router.get("/trending")
async def trending_ads(
    country: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Get longest-running (likely profitable) ads."""
    es = get_es_client()
    try:
        return await es_trending(es, country=country, limit=limit)
    finally:
        await es.close()


@router.get("/{ad_id}")
async def get_ad(ad_id: str):
    """Get full ad details by ID."""
    es = get_es_client()
    try:
        result = await es.get(index="ads", id=ad_id)
        return {**result["_source"], "id": result["_id"]}
    except Exception:
        raise HTTPException(status_code=404, detail="Ad not found")
    finally:
        await es.close()
