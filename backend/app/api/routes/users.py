"""
Users API routes — per-user saved ads ("swipe file"), grouped by board, plus
plan/credit usage.

Every route requires a verified Clerk session token (Authorization: Bearer),
enforced by the get_user_id dependency — the old spoofable X-User-Id header
is no longer trusted (except in DEBUG when Clerk isn't configured at all).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from sqlalchemy import select, delete, func

from app.core.auth import get_user_id
from app.core.credits import _active_subscription, get_usage as credits_usage
from app.core.database import async_session
from app.core.elasticsearch import get_es_client
from app.models.saved import SavedAd

router = APIRouter()

# Free-tier swipe-file cap (PRICING.md §2: "Saved boards — 10 / unlimited").
# Counts DISTINCT ads, not rows: the same ad on two boards is one saved ad.
FREE_SAVED_CAP = 10


class SaveRequest(BaseModel):
    ad_id: str
    board: str = "Default"


class UnsaveRequest(BaseModel):
    ad_id: str
    board: Optional[str] = None  # None = remove from EVERY board


@router.post("/save")
async def save_ad(req: SaveRequest, uid: str = Depends(get_user_id)):
    """Save an ad to a board (idempotent). Free plan caps the swipe file."""
    board = (req.board or "Default").strip()[:48] or "Default"
    async with async_session() as db:
        exists = await db.scalar(
            select(SavedAd.id).where(
                SavedAd.user_id == uid,
                SavedAd.ad_id == req.ad_id,
                SavedAd.board == board,
            )
        )
        if exists:
            return {"status": "saved", "board": board, "ad_id": req.ad_id}

        plan, _bonus = await _active_subscription(db, uid)
        if plan == "free":
            distinct_ads = await db.scalar(
                select(func.count(func.distinct(SavedAd.ad_id)))
                .where(SavedAd.user_id == uid)
            ) or 0
            # Re-boarding an already-saved ad never counts against the cap.
            already = await db.scalar(
                select(func.count()).select_from(SavedAd).where(
                    SavedAd.user_id == uid, SavedAd.ad_id == req.ad_id
                )
            ) or 0
            if distinct_ads >= FREE_SAVED_CAP and not already:
                raise HTTPException(status_code=402, detail={
                    "error": "saved_cap",
                    "message": f"The free plan holds {FREE_SAVED_CAP} saved ads. "
                               "Upgrade to Pro for an unlimited swipe file.",
                })

        db.add(SavedAd(user_id=uid, ad_id=req.ad_id, board=board))
        await db.commit()
    return {"status": "saved", "board": board, "ad_id": req.ad_id}


@router.post("/unsave")
async def unsave_ad(req: UnsaveRequest, uid: str = Depends(get_user_id)):
    """Remove an ad from one board, or from every board when none is given.

    The board-less form exists for the bookmark toggle: it must remove the ad
    no matter which board it was saved to (a "Default"-only delete silently
    left ads saved on other boards, and they reappeared on the next refresh).
    """
    async with async_session() as db:
        q = delete(SavedAd).where(
            SavedAd.user_id == uid,
            SavedAd.ad_id == req.ad_id,
        )
        if req.board:
            q = q.where(SavedAd.board == req.board)
        await db.execute(q)
        await db.commit()
    return {"status": "removed", "board": req.board, "ad_id": req.ad_id}


@router.get("/saved/ids")
async def saved_ids(uid: str = Depends(get_user_id)):
    """Lightweight: just the set of saved ad ids (for showing save state in lists)."""
    async with async_session() as db:
        rows = await db.execute(
            select(SavedAd.ad_id).where(SavedAd.user_id == uid)
        )
        return {"ad_ids": sorted({r[0] for r in rows.all()})}


@router.get("/saved")
async def saved_boards(uid: str = Depends(get_user_id)):
    """Boards summary: name + count, plus total."""
    async with async_session() as db:
        rows = await db.execute(
            select(SavedAd.board, func.count(SavedAd.id))
            .where(SavedAd.user_id == uid)
            .group_by(SavedAd.board)
        )
        boards = [{"name": b, "count": c} for b, c in rows.all()]
    total = sum(b["count"] for b in boards)
    return {"boards": boards, "total": total}


@router.get("/saved/ads")
async def saved_ad_docs(
    uid: str = Depends(get_user_id),
    board: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Full ad docs for the user's saved ads (newest first), hydrated from ES."""
    async with async_session() as db:
        q = select(SavedAd.ad_id).where(SavedAd.user_id == uid)
        if board:
            q = q.where(SavedAd.board == board)
        q = q.order_by(SavedAd.created_at.desc()).limit(limit)
        ids = [r[0] for r in (await db.execute(q)).all()]

    if not ids:
        return {"results": [], "total": 0}

    es = get_es_client()
    try:
        res = await es.mget(index="ads", ids=ids)
    finally:
        await es.close()

    # Preserve saved order (newest first); drop any that no longer exist in the index.
    by_id = {d["_id"]: d for d in res["docs"] if d.get("found")}
    results = [
        {**by_id[i]["_source"], "id": i}
        for i in ids
        if i in by_id
    ]
    return {"results": results, "total": len(results)}


@router.get("/usage")
async def get_usage(uid: str = Depends(get_user_id)):
    """The user's active plan and real AI-credit usage for the current month."""
    return await credits_usage(uid)
