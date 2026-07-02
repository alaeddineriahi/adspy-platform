"""
Database setup — async SQLAlchemy engine + session.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# echo only when DEBUG_SQL is explicitly on — DEBUG alone floods startup with the
# create_all type-introspection queries (made restarts take ~40s).
engine = create_async_engine(settings.DATABASE_URL, echo=getattr(settings, "DEBUG_SQL", False))
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    """Create all tables. Safe to call on startup."""
    from app.models import saved, billing, watchlist, admin  # noqa: F401  (register models)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
