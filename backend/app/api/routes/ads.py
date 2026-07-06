"""
Ads API routes — search, trending, detail.
Wired to Elasticsearch for full-text search with filters.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional

from app.core.auth import get_user_id
from app.core.credits import get_plan, FREE_SEARCH_RESULT_CAP, FREE_POWER_FILTERS
from app.core.elasticsearch import (
    get_es_client,
    public_ad,
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
    uid: str = Depends(get_user_id),
):
    """Search ads with full-text query and filters.

    Requires a signed-in user (anonymous callers can no longer scrape the
    catalog). The free plan sees the top FREE_SEARCH_RESULT_CAP money-ranked
    winners and can't use the power filters; paid plans get everything.
    """
    plan = await get_plan(uid)
    free = plan == "free"

    # Free tier: no power filters, capped depth, single page.
    filters_locked = False
    if free and not FREE_POWER_FILTERS:
        if any(v is not None for v in (momentum, min_days, min_variants, min_spend)):
            filters_locked = True
        momentum = min_days = min_variants = min_spend = None
    if free:
        page = 1
        limit = min(limit, FREE_SEARCH_RESULT_CAP)

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
    finally:
        await es.close()

    results["plan"] = plan
    if free:
        # Cap what free can see (and page through) so Pro has a reason to exist.
        capped_total = min(results.get("total", 0), FREE_SEARCH_RESULT_CAP)
        results["results"] = results["results"][:FREE_SEARCH_RESULT_CAP]
        results["total"] = capped_total
        results["pages"] = 1
        results["free_capped"] = True
        results["filters_locked"] = filters_locked
        results["result_cap"] = FREE_SEARCH_RESULT_CAP
    return results


@router.get("/trending")
async def trending_ads(
    country: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    uid: str = Depends(get_user_id),
):
    """Get longest-running (likely profitable) ads."""
    if await get_plan(uid) == "free":
        limit = min(limit, FREE_SEARCH_RESULT_CAP)
    es = get_es_client()
    try:
        return await es_trending(es, country=country, limit=limit)
    finally:
        await es.close()


@router.get("/{ad_id}")
async def get_ad(ad_id: str, uid: str = Depends(get_user_id)):
    """Get full ad details by ID (signed-in users only)."""
    es = get_es_client()
    try:
        result = await es.get(index="ads", id=ad_id)
        return {**public_ad(result["_source"]), "id": result["_id"]}
    except Exception:
        raise HTTPException(status_code=404, detail="Ad not found")
    finally:
        await es.close()
