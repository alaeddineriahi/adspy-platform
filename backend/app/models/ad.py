"""
Ad SQLAlchemy model — PostgreSQL storage for ad metadata.
"""

import uuid
import enum

from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Platform(str, enum.Enum):
    meta = "meta"
    tiktok = "tiktok"
    google = "google"


class AdFormat(str, enum.Enum):
    image = "image"
    video = "video"
    carousel = "carousel"


class Ad(Base):
    __tablename__ = "ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(Enum(Platform), nullable=False, index=True)
    advertiser_name = Column(Text, nullable=False, index=True)
    advertiser_id = Column(String(255), nullable=False, index=True)
    ad_id = Column(String(255), unique=True, nullable=False)
    country = Column(String(10), nullable=False, index=True)
    language = Column(String(10), nullable=False)
    ad_format = Column(Enum(AdFormat), nullable=False, index=True)
    copy_text = Column(Text, default="")
    cta_text = Column(String(255), default="")
    landing_page = Column(Text, default="")
    media_urls = Column(JSON, default=list)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
