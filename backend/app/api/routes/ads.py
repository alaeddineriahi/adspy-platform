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
from app.scraping.meta_official import ingest as meta_ingest

router = APIRouter()


@router.post("/ingest")
async def ingest_meta_ads(
    country: str = Query("TN", description="ISO country code"),
    q: str = Query("", description="Search terms (optional)"),
    limit: int = Query(50, ge=1, le=100),
    ad_active_status: str = Query("ALL", description="ACTIVE, INACTIVE, or ALL"),
    ad_type: str = Query("ALL", description="ALL or POLITICAL_AND_ISSUE_ADS"),
):
    """Pull ads from the official Meta Ad Library and index them into Elasticsearch."""
    try:
        return await meta_ingest(
            country=country,
            search_terms=q,
            limit=limit,
            ad_active_status=ad_active_status,
            ad_type=ad_type,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/search")
async def search_ads(
    q: Optional[str] = Query(None, description="Search query"),
    platform: Optional[str] = Query(None, description="meta or tiktok"),
    format: Optional[str] = Query(None, description="image, video, or carousel"),
    country: Optional[str] = Query(None, description="ISO country code"),
    language: Optional[str] = Query(None, description="en, ar, or fr"),
    active: Optional[bool] = Query(None, description="Active ads only"),
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
