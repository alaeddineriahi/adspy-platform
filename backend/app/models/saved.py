"""
SavedAd SQLAlchemy model — a user's saved ads ("swipe file"), grouped by board.

Persisted per user (Clerk user id) so a saved winner survives restarts and is
scoped to the account, unlike the old global in-memory dict.
"""

import uuid

from sqlalchemy import Column, String, DateTime, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class SavedAd(Base):
    __tablename__ = "saved_ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    ad_id = Column(String(255), nullable=False)          # ES doc id
    board = Column(String(255), nullable=False, default="Default")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # One row per (user, ad, board) — saving twice is a no-op.
        UniqueConstraint("user_id", "ad_id", "board", name="uq_saved_user_ad_board"),
        Index("ix_saved_user_created", "user_id", "created_at"),
    )
