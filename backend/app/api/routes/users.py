"""
Users API routes — per-user saved ads ("swipe file"), grouped by board.

Persisted in Postgres and scoped to the Clerk user id (sent as the `X-User-Id`
header by the frontend). Falls back to "anonymous" so it still works in local dev
before auth is fully wired. Backend Clerk-JWT verification is a later hardening step.
"""

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel
from typing import Optional

from sqlalchemy import select, delete, func

from app.core.database import async_session
from app.core.elasticsearch import get_es_client
from app.models.saved import SavedAd

router = APIRouter()


def _uid(x_user_id: Optional[str]) -> str:
    return (x_user_id or "").strip() or "anonymous"


class SaveRequest(BaseModel):
    ad_id: str
    board: str = "Default"


@router.post("/save")
async def save_ad(req: SaveRequest, x_user_id: Optional[str] = Header(None)):
    """Save an ad to a board (idempotent)."""
    uid = _uid(x_user_id)
    async with async_session() as db:
        exists = await db.scalar(
            select(SavedAd.id).where(
                SavedAd.user_id == uid,
                SavedAd.ad_id == req.ad_id,
                SavedAd.board == req.board,
            )
        )
        if not exists:
            db.add(SavedAd(user_id=uid, ad_id=req.ad_id, board=req.board))
            await db.commit()
    return {"status": "saved", "board": req.board, "ad_id": req.ad_id}


@router.post("/unsave")
async def unsave_ad(req: SaveRequest, x_user_id: Optional[str] = Header(None)):
    """Remove an ad from a board (idempotent)."""
    uid = _uid(x_user_id)
    async with async_session() as db:
        await db.execute(
            delete(SavedAd).where(
                SavedAd.user_id == uid,
                SavedAd.ad_id == req.ad_id,
                SavedAd.board == req.board,
            )
        )
        await db.commit()
    return {"status": "removed", "board": req.board, "ad_id": req.ad_id}


@router.get("/saved/ids")
async def saved_ids(x_user_id: Optional[str] = Header(None)):
    """Lightweight: just the set of saved ad ids (for showing save state in lists)."""
    uid = _uid(x_user_id)
    async with async_session() as db:
        rows = await db.execute(
            select(SavedAd.ad_id).where(SavedAd.user_id == uid)
        )
        return {"ad_ids": sorted({r[0] for r in rows.all()})}


@router.get("/saved")
async def saved_boards(x_user_id: Optional[str] = Header(None)):
    """Boards summary: name + count, plus total."""
    uid = _uid(x_user_id)
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
    x_user_id: Optional[str] = Header(None),
    board: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """Full ad docs for the user's saved ads (newest first), hydrated from ES."""
    uid = _uid(x_user_id)
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
async def get_usage(x_user_id: Optional[str] = Header(None)):
    """Get the user's plan and credit usage. (Credit metering is a later track — placeholder.)"""
    return {
        "plan": "free",
        "searches_today": 0,
        "searches_limit": 20,
        "credits_remaining": 5,
        "credits_limit": 5,
    }
