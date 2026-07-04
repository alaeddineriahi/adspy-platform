"""
Server-side Product Dossier cache.

The intelligence in a dossier is per-AD, not per-user — once compiled, the
same product facts serve everyone. Caching it makes repeat requests instant,
immune to LLM flakiness, and cheaper for the user (the route charges 1 credit
for a cache hit vs 2 for fresh compilation).
"""

from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class DossierCache(Base):
    __tablename__ = "dossier_cache"

    ad_id = Column(String(64), primary_key=True)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
