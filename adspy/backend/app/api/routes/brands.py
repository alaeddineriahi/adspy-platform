from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/search")
async def search_brands(q: str = Query(..., min_length=1)):
    """Search advertisers/brands."""
    return {"results": [], "total": 0}


@router.get("/{brand_id}/ads")
async def get_brand_ads(
    brand_id: str,
    platform: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all ads for a specific brand."""
    return {"results": [], "total": 0, "page": page}


@router.post("/watchlist")
async def add_to_watchlist(brand_id: str):
    """Add brand to user's watchlist."""
    return {"status": "added"}


@router.get("/watchlist")
async def get_watchlist():
    """Get user's brand watchlist."""
    return {"brands": []}
