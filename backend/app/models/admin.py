"""
Admin-only models: audit trail + per-user account flags (ban/suspend).

Every admin mutation (plan override, credit grant, ban, ad deletion,
impersonation) writes an AuditLog row — the accountability trail for actions
that bypass normal user-facing flows.
"""

import uuid

from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_id = Column(String(255), nullable=False, index=True)
    action = Column(String(64), nullable=False)              # e.g. "plan_override", "ban", "ad_delete"
    target_user_id = Column(String(255), nullable=True, index=True)
    detail = Column(Text, nullable=True)                      # human-readable summary
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserFlag(Base):
    __tablename__ = "user_flags"

    user_id = Column(String(255), primary_key=True)
    banned = Column(Boolean, nullable=False, default=False)
    ban_reason = Column(String(512), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
