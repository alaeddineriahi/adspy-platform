"""
WatchedBrand — a user's brand watchlist, persisted per Clerk user id.

Replaces the old module-level `_WATCHLIST` list, which was shared by every
user and wiped on each restart.
"""

import uuid

from sqlalchemy import Column, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class WatchedBrand(Base):
    __tablename__ = "watched_brands"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    brand_id = Column(String(255), nullable=False)       # advertiser_id / page id
    brand_name = Column(String(512), nullable=True)      # denormalized for display
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "brand_id", name="uq_watch_user_brand"),
    )
