"""
Konnect.network payment gateway integration for TND subscriptions.
Docs: https://docs.konnect.network

Amount is in MILLIMES (1 TND = 1000 millimes).
"""

import httpx
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from app.core.config import settings


class KonnectEnv(str, Enum):
    SANDBOX = "https://api.preprod.konnect.network/api/v2"
    PRODUCTION = "https://api.konnect.network/api/v2"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class KonnectPayment:
    pay_url: str
    payment_ref: str


@dataclass
class PaymentDetails:
    payment_ref: str
    status: str
    amount: int
    completed_at: Optional[str] = None
    order_id: Optional[str] = None
    payer_email: Optional[str] = None


# Plan prices in MILLIMES (1 TND = 1000 millimes)
PLAN_PRICES = {
    "pro": 29_000,       # 29 TND/month
    "agency": 79_000,    # 79 TND/month
}

PLAN_DESCRIPTIONS = {
    "pro": "AdSpy Pro - Recherche illimitée, 50 crédits IA, brand spy",
    "agency": "AdSpy Agency - Tout illimité, 200 crédits IA, 25 marques",
}


class KonnectClient:
    def __init__(self):
        self.api_key = settings.KONNECT_API_KEY
        self.wallet_id = settings.KONNECT_WALLET_ID
        self.base_url = (
            KonnectEnv.SANDBOX if settings.KONNECT_SANDBOX
            else KonnectEnv.PRODUCTION
        )
        self.webhook_url = f"{settings.API_BASE_URL}/api/payments/webhook/konnect"

    async def init_subscription(
        self,
        plan: str,
        user_email: str,
        user_id: str,
        first_name: str = "",
        last_name: str = "",
        phone: str = "",
    ) -> KonnectPayment:
        """Create a payment for a subscription plan."""
        if plan not in PLAN_PRICES:
            raise ValueError(f"Unknown plan: {plan}")

        payload = {
            "receiverWalletId": self.wallet_id,
            "token": "TND",
            "amount": PLAN_PRICES[plan],
            "type": "immediate",
            "description": PLAN_DESCRIPTIONS[plan],
            "acceptedPaymentMethods": ["wallet", "bank_card", "e-DINAR"],
            "lifespan": 30,
            "checkoutForm": True,
            "addPaymentFeesToAmount": False,
            "firstName": first_name,
            "lastName": last_name,
            "phoneNumber": phone,
            "email": user_email,
            "orderId": f"sub_{user_id}_{plan}",
            "webhook": self.webhook_url,
            "theme": "dark",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/payments/init-payment",
                json=payload,
                headers={"x-api-key": self.api_key},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

        return KonnectPayment(
            pay_url=data["payUrl"],
            payment_ref=data["paymentRef"],
        )

    async def get_payment(self, payment_ref: str) -> PaymentDetails:
        """Check payment status."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/payments/{payment_ref}",
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

        payment = data.get("payment", data)
        transactions = payment.get("transactions", [])
        status = "completed" if any(
            t.get("status") == "completed" for t in transactions
        ) else "pending"

        return PaymentDetails(
            payment_ref=payment_ref,
            status=status,
            amount=payment.get("amount", 0),
            completed_at=payment.get("completedAt"),
            order_id=payment.get("orderId"),
            payer_email=payment.get("email"),
        )


konnect = KonnectClient()
