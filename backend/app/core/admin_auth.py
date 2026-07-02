"""
Admin gate — require_admin builds on get_user_id and additionally checks the
caller's Clerk public_metadata.role == "admin".

Role lives in Clerk (not a hardcoded env-var allowlist) so promoting a new
admin is `python set_admin_role.py <email>` (or the Clerk dashboard) — no
redeploy needed. Cached briefly in-process since this hits Clerk's API.
"""

import time

from fastapi import Depends, HTTPException

from app.core.auth import get_user_id
from app.core.clerk_admin import get_user

_CACHE_TTL = 30  # seconds
_cache: dict[str, tuple[float, bool]] = {}


async def _is_admin(user_id: str) -> bool:
    now = time.monotonic()
    cached = _cache.get(user_id)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    user = await get_user(user_id)
    is_admin = bool(user and user.get("role") == "admin")
    _cache[user_id] = (now, is_admin)
    return is_admin


async def require_admin(uid: str = Depends(get_user_id)) -> str:
    if not await _is_admin(uid):
        raise HTTPException(status_code=403, detail="Admin access required")
    return uid
