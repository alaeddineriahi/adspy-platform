from fastapi import APIRouter

router = APIRouter()


@router.get("/saved")
async def get_saved_ads():
    """Get user's saved ads and boards."""
    return {"boards": [], "total": 0}


@router.post("/save")
async def save_ad(ad_id: str, board: str = "Default"):
    """Save an ad to a board."""
    return {"status": "saved"}


@router.get("/usage")
async def get_usage():
    """Get user's plan and credit usage."""
    return {
        "plan": "free",
        "searches_today": 0,
        "searches_limit": 20,
        "credits_remaining": 5,
        "credits_limit": 5,
    }
