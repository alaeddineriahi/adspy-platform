"""
Payment routes - Konnect (primary) + Flouci (secondary).
All prices in TND for the Tunisian market; plan numbers live in PRICING.md.

Flow: an authenticated user hits /subscribe -> we create the gateway checkout
AND store a PaymentIntent binding payment_ref -> (user, plan). The webhook /
verification endpoints then look the ref up locally and activate the
subscription in Postgres — nothing in the callback is trusted for identity.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from sqlalchemy import select

from app.core.auth import get_user_id
from app.core.credits import PLAN_CREDITS, activate_subscription
from app.core.database import async_session
from app.models.billing import PaymentIntent
from app.payments.konnect import konnect, PLAN_PRICES
from app.payments.flouci import flouci

logger = logging.getLogger("adspy.payments")
router = APIRouter(prefix="/payments", tags=["payments"])


class SubscribeRequest(BaseModel):
    plan: str  # "pro" or "agency"
    payment_method: str = "konnect"  # "konnect" or "flouci"
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    phone: Optional[str] = ""


class SubscribeResponse(BaseModel):
    pay_url: str
    payment_ref: str
    amount_tnd: float
    plan: str


async def _store_intent(payment_ref: str, user_id: str, plan: str, provider: str) -> None:
    async with async_session() as db:
        db.add(PaymentIntent(payment_ref=payment_ref, user_id=user_id,
                             plan=plan, provider=provider))
        await db.commit()


async def _complete_intent(payment_ref: str) -> Optional[PaymentIntent]:
    """Mark an intent completed and activate the subscription. Idempotent."""
    async with async_session() as db:
        intent = await db.scalar(
            select(PaymentIntent).where(PaymentIntent.payment_ref == payment_ref)
        )
        if intent is None:
            return None
        already_done = intent.status == "completed"
        intent.status = "completed"
        await db.commit()
    if not already_done:
        await activate_subscription(intent.user_id, intent.plan, payment_ref=payment_ref)
        logger.info("Activated %s for user %s (ref %s)", intent.plan, intent.user_id, payment_ref)
    return intent


# --- Subscription endpoints ---

@router.post("/subscribe", response_model=SubscribeResponse)
async def create_subscription(req: SubscribeRequest, uid: str = Depends(get_user_id)):
    """Create a payment link for a subscription plan (requires a signed-in user)."""
    if req.plan not in PLAN_PRICES:
        raise HTTPException(400, f"Invalid plan. Choose: {list(PLAN_PRICES.keys())}")

    amount = PLAN_PRICES[req.plan]

    if req.payment_method == "flouci":
        payment = await flouci.create_payment(
            amount_millimes=amount,
            description=f"AdSpy {req.plan} subscription",
        )
        await _store_intent(payment.payment_id, uid, req.plan, "flouci")
        return SubscribeResponse(
            pay_url=payment.pay_url,
            payment_ref=payment.payment_id,
            amount_tnd=amount / 1000,
            plan=req.plan,
        )

    # Default: Konnect
    payment = await konnect.init_subscription(
        plan=req.plan,
        user_email="",
        user_id=uid,
        first_name=req.first_name or "",
        last_name=req.last_name or "",
        phone=req.phone or "",
    )
    await _store_intent(payment.payment_ref, uid, req.plan, "konnect")
    return SubscribeResponse(
        pay_url=payment.pay_url,
        payment_ref=payment.payment_ref,
        amount_tnd=amount / 1000,
        plan=req.plan,
    )


# --- Webhook endpoints ---

@router.get("/webhook/konnect")
async def konnect_webhook(payment_ref: str):
    """Konnect sends a GET request with payment_ref as query param."""
    # Always re-verify with Konnect's API — never trust the callback alone.
    details = await konnect.get_payment(payment_ref)

    if details.status == "completed":
        intent = await _complete_intent(payment_ref)
        if intent is None:
            logger.warning("Konnect webhook for unknown payment_ref %s", payment_ref)
            return {"status": "ok", "payment": "completed", "subscription": "unknown_ref"}
        return {"status": "ok", "payment": "completed", "subscription": "activated"}

    return {"status": "pending"}


@router.get("/verify/{payment_id}")
async def verify_flouci_payment(payment_id: str):
    """Verify a Flouci payment status."""
    status = await flouci.verify_payment(payment_id)
    if status.status == "SUCCESS":
        intent = await _complete_intent(payment_id)
        if intent is None:
            logger.warning("Flouci verify for unknown payment_id %s", payment_id)
            return {"status": "ok", "payment": "completed", "subscription": "unknown_ref"}
        return {"status": "ok", "payment": "completed", "subscription": "activated"}
    return {"status": status.status.lower()}


# --- Pricing info ---

@router.get("/plans")
async def get_plans():
    """Available plans — numbers kept in sync with PRICING.md."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_tnd": 0,
                "searches_per_day": 20,
                "ai_credits_per_month": PLAN_CREDITS["free"],
                "saved_ads": 10,
                "brand_spy": False,
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_tnd": PLAN_PRICES["pro"] / 1000,
                "searches_per_day": -1,  # unlimited
                "ai_credits_per_month": PLAN_CREDITS["pro"],
                "saved_ads": -1,
                "brand_spy": True,
                "brand_spy_limit": 5,
            },
            {
                "id": "agency",
                "name": "Agency",
                "price_tnd": PLAN_PRICES["agency"] / 1000,
                "searches_per_day": -1,
                "ai_credits_per_month": PLAN_CREDITS["agency"],
                "saved_ads": -1,
                "brand_spy": True,
                "brand_spy_limit": 25,
            },
        ],
        "currency": "TND",
        "payment_methods": ["konnect", "flouci"],
        "accepted": ["bank_card", "e-DINAR", "wallet"],
    }
