"""
Media-buyer co-pilot routes.

POST /api/mediabuyer/chat — streams the assistant reply as plain text so the
frontend can render tokens as they arrive.

The `/capabilities` endpoint advertises the seam for the future live-Meta phase
(chat is on now; meta_execution flips true once the executor lands).
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Optional

from app.ai.media_buyer import stream_chat
from app.core.config import settings

router = APIRouter()

# Cap history so a runaway client can't blow the context window / cost.
_MAX_MESSAGES = 24


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class BuyerProfile(BaseModel):
    """The user's setup, so advice is tailored to their means."""
    country: Optional[str] = None
    currency: Optional[str] = None
    budget: Optional[float] = None          # daily budget they can afford, local currency
    creatives_count: Optional[int] = None
    creative_types: Optional[list[str]] = None
    experience: Optional[str] = None        # none | beginner | intermediate
    platform: Optional[str] = None          # meta | tiktok
    product: Optional[str] = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    ad_id: Optional[str] = None
    profile: Optional[BuyerProfile] = None


@router.post("/chat")
async def chat(req: ChatRequest):
    """Stream the media-buyer's reply (text/plain, token-by-token)."""
    history = [m.model_dump() for m in req.messages if m.content.strip()][-_MAX_MESSAGES:]
    profile = req.profile.model_dump(exclude_none=True) if req.profile else None

    async def gen():
        try:
            async for delta in stream_chat(history, ad_id=req.ad_id, profile=profile):
                yield delta
        except Exception as e:  # surface a readable error inline in the stream
            yield f"\n\n⚠️ The media buyer hit an error: {e}"

    return StreamingResponse(
        gen(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/capabilities")
async def capabilities():
    """What the co-pilot can do — flips as live Meta execution is added."""
    return {
        "chat": True,
        "grounded_in_spy_data": True,
        "meta_execution": bool(
            getattr(settings, "META_ACCESS_TOKEN", "")
            and getattr(settings, "META_AD_ACCOUNT_ID", "")
        ),  # advisory-only until an executor + ad account are wired
        "provider": getattr(settings, "AI_PROVIDER", "groq"),
    }
