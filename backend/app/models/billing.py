"""
Billing models — subscriptions, monthly AI-credit usage, payment intents.

A PaymentIntent row is written when a checkout link is created, binding the
gateway's payment_ref to the authenticated user + plan. Webhooks/verification
look the ref up here instead of trusting anything in the callback.
"""

import uuid

from sqlalchemy import Column, String, Integer, Boolean, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    plan = Column(String(32), nullable=False, default="free")          # free | pro | agency
    status = Column(String(32), nullable=False, default="active")      # active | cancelled
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    payment_ref = Column(String(255), nullable=True)                   # last successful payment
    # Admin-granted extra credits on top of the plan's monthly allowance (comps,
    # goodwill, support fixes) — added to PLAN_CREDITS[plan] in credits.py.
    credit_bonus = Column(Integer, nullable=False, default=0)
    is_comp = Column(Boolean, nullable=False, default=False)           # admin override, not a real payment
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CreditUsage(Base):
    __tablename__ = "credit_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    period = Column(String(7), nullable=False)                         # "YYYY-MM" (UTC)
    used = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("user_id", "period", name="uq_credit_user_period"),
    )


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_ref = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    plan = Column(String(32), nullable=False)
    provider = Column(String(32), nullable=False)                      # konnect | flouci
    status = Column(String(32), nullable=False, default="pending")     # pending | completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
