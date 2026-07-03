"""
Brand intelligence models.

BrandSnapshot is one deep-dive observation of an advertiser: "on this date,
this page had N ads live in the Ad Library." A time series of these rows is
the brand's *trajectory* — a page going 5 → 60 live ads in three weeks is the
strongest "they found a winner and are scaling it" signal we can observe.
"""

import uuid

from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class BrandSnapshot(Base):
    __tablename__ = "brand_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String(64), nullable=False, index=True)
    page_name = Column(String(255), nullable=False)
    country = Column(String(8), nullable=False, default="ALL")  # scope of the count
    live_ads = Column(Integer, nullable=False)                  # ads live at capture time
    captured_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
