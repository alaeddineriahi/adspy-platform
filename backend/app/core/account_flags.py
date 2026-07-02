"""Small, separate from credits.py to avoid import cycles: auth.py needs this,
credits.py doesn't need to know about it."""

from sqlalchemy import select

from app.core.database import async_session
from app.models.admin import UserFlag


async def is_banned(user_id: str) -> bool:
    async with async_session() as db:
        banned = await db.scalar(select(UserFlag.banned).where(UserFlag.user_id == user_id))
        return bool(banned)
