"""Ban-flag lookup used by auth on EVERY authenticated request — so it's
cached with a short TTL instead of hitting Postgres each time. The admin
ban/unban route calls invalidate() so a suspension still lands instantly.

Small, separate from credits.py to avoid import cycles: auth.py needs this,
credits.py doesn't need to know about it."""

import time

from sqlalchemy import select

from app.core.database import async_session
from app.models.admin import UserFlag

_CACHE_TTL = 60  # seconds
_cache: dict[str, tuple[float, bool]] = {}


def invalidate(user_id: str) -> None:
    _cache.pop(user_id, None)


async def is_banned(user_id: str) -> bool:
    now = time.monotonic()
    cached = _cache.get(user_id)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    async with async_session() as db:
        banned = bool(
            await db.scalar(select(UserFlag.banned).where(UserFlag.user_id == user_id))
        )

    if len(_cache) > 10_000:  # safety valve, never grows unbounded
        _cache.clear()
    _cache[user_id] = (now, banned)
    return banned
