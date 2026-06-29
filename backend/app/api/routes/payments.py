"""
Payment routes - Konnect (primary) + Flouci (secondary).
All prices in TND for Tunisian market.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional
from app.payments.konnect import konnect, PLAN_PRICES
from app.payments.flouci import flouci

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


# --- Subscription endpoints ---

@router.post("/subscribe", response_model=SubscribeResponse)
async def create_subscription(req: SubscribeRequest):
    """Create a payment link for a subscription plan."""
    if req.plan not in PLAN_PRICES:
        raise HTTPException(400, f"Invalid plan. Choose: {list(PLAN_PRICES.keys())}")

    amount = PLAN_PRICES[req.plan]

    if req.payment_method == "flouci":
        payment = await flouci.create_payment(
            amount_millimes=amount,
            description=f"AdSpy {req.plan} subscription",
        )
        return SubscribeResponse(
            pay_url=payment.pay_url,
            payment_ref=payment.payment_id,
            amount_tnd=amount / 1000,
            plan=req.plan,
        )
    else:
        # Default: Konnect
        payment = await konnect.init_subscription(
            plan=req.plan,
            user_email="",  # filled from auth context in production
            user_id="temp",
            first_name=req.first_name or "",
            last_name=req.last_name or "",
            phone=req.phone or "",
        )
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
    details = await konnect.get_payment(payment_ref)

    if details.status == "completed":
        # TODO: activate user subscription in DB
        # parse order_id format: sub_{user_id}_{plan}
        parts = (details.order_id or "").split("_")
        if len(parts) >= 3:
            user_id = parts[1]
            plan = parts[2]
            # await activate_subscription(user_id, plan)
        return {"status": "ok", "payment": "completed"}

    return {"status": "pending"}


@router.get("/verify/{payment_id}")
async def verify_flouci_payment(payment_id: str):
    """Verify a Flouci payment status."""
    status = await flouci.verify_payment(payment_id)
    if status.status == "SUCCESS":
        # TODO: activate user subscription in DB
        return {"status": "ok", "payment": "completed"}
    return {"status": status.status.lower()}


# --- Pricing info ---

@router.get("/plans")
async def get_plans():
    """Return available plans with TND pricing."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_tnd": 0,
                "searches_per_day": 20,
                "ai_credits_per_month": 5,
                "saved_ads": 10,
                "brand_spy": False,
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_tnd": 29,
                "searches_per_day": -1,  # unlimited
                "ai_credits_per_month": 50,
                "saved_ads": -1,
                "brand_spy": True,
                "brand_spy_limit": 5,
            },
            {
                "id": "agency",
                "name": "Agency",
                "price_tnd": 79,
                "searches_per_day": -1,
                "ai_credits_per_month": 200,
                "saved_ads": -1,
                "brand_spy": True,
                "brand_spy_limit": 25,
            },
        ],
        "currency": "TND",
        "payment_methods": ["konnect", "flouci"],
        "accepted": ["bank_card", "e-DINAR", "wallet"],
    }
