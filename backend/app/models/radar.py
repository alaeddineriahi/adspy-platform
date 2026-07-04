"""
Trend Radar events — "what started printing money since you last looked."

One row = one market signal detected by the ingestion sweep:
  new_hot          — a product entered the index already scaling fast
  momentum_flip    — a tracked ad flipped steady/proven → hot (scaling NOW)
  trend_arrival    — an ad previously seen only in global trend markets just
                     appeared in a MENA market (the wave is arriving — be first)
  brand_escalation — a deep-dived brand's live-ad count jumped (budget pouring in)
  brand_expansion  — a tracked brand shipped a batch of new winning creatives

Events are generated at sweep time (no LLM, no polling — pure diffing of state
we already compute) and pruned after RETENTION_DAYS. The Radar page reads them;
the free tier sees a locked teaser (see routes/radar.py).
"""

import uuid

from sqlalchemy import Column, String, Integer, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class RadarEvent(Base):
    __tablename__ = "radar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(32), nullable=False, index=True)
    country = Column(String(8), nullable=True, index=True)     # market the signal fired in
    ad_id = Column(String(64), nullable=True)
    advertiser_id = Column(String(64), nullable=True, index=True)
    advertiser_name = Column(String(255), nullable=True)
    headline = Column(String(255), nullable=False)             # card title
    detail = Column(String(512), nullable=True)                # the "why" line
    magnitude = Column(Integer, nullable=True)                 # e.g. +29 live ads, 14 variants
    heat = Column(Float, nullable=True)
    thumbnail = Column(String(1024), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
