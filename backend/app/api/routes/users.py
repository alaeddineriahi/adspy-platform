"""
Users API routes — saved ads / boards and plan usage.

In-memory storage for now; wire to PostgreSQL for production.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory store: board name -> list of ad ids
_BOARDS: dict[str, list[str]] = {"Default": []}


class SaveRequest(BaseModel):
    ad_id: str
    board: str = "Default"


@router.get("/saved")
async def get_saved_ads():
    """Get the user's saved ads grouped by board."""
    boards = [
        {"name": name, "ad_ids": ads, "count": len(ads)}
        for name, ads in _BOARDS.items()
    ]
    total = sum(len(ads) for ads in _BOARDS.values())
    return {"boards": boards, "total": total}


@router.post("/save")
async def save_ad(req: SaveRequest):
    """Save an ad to a board."""
    _BOARDS.setdefault(req.board, [])
    if req.ad_id not in _BOARDS[req.board]:
        _BOARDS[req.board].append(req.ad_id)
    return {"status": "saved", "board": req.board}


@router.get("/usage")
async def get_usage():
    """Get the user's plan and credit usage."""
    return {
        "plan": "free",
        "searches_today": 0,
        "searches_limit": 20,
        "credits_remaining": 5,
        "credits_limit": 5,
    }
