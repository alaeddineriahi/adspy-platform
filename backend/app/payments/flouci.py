"""
Flouci payment gateway integration.
Docs: https://docs.flouci.com

Secondary payment option for mobile wallet users in Tunisia.
Amount in MILLIMES (1 TND = 1000 millimes).
"""

import httpx
from dataclasses import dataclass
from typing import Optional
from app.core.config import settings


FLOUCI_BASE_URL = "https://developers.flouci.com/api"


@dataclass
class FlouciPayment:
    pay_url: str
    payment_id: str


@dataclass
class FlouciPaymentStatus:
    payment_id: str
    status: str  # SUCCESS, PENDING, FAILURE
    amount: int


class FlouciClient:
    def __init__(self):
        self.app_token = settings.FLOUCI_APP_TOKEN
        self.app_secret = settings.FLOUCI_APP_SECRET
        self.success_url = f"{settings.FRONTEND_URL}/settings/billing?status=success"
        self.fail_url = f"{settings.FRONTEND_URL}/settings/billing?status=failed"

    async def create_payment(
        self,
        amount_millimes: int,
        description: str = "AdSpy subscription",
    ) -> FlouciPayment:
        """Initiate a Flouci payment."""
        payload = {
            "app_token": self.app_token,
            "app_secret": self.app_secret,
            "amount": amount_millimes,
            "accept_card": "true",
            "session_timeout_secs": 1800,
            "success_link": self.success_url,
            "fail_link": self.fail_url,
            "developer_tracking_id": description,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{FLOUCI_BASE_URL}/generate_payment",
                json=payload,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

        return FlouciPayment(
            pay_url=data["result"]["link"],
            payment_id=data["result"]["payment_id"],
        )

    async def verify_payment(self, payment_id: str) -> FlouciPaymentStatus:
        """Check payment status."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{FLOUCI_BASE_URL}/verify_payment/{payment_id}",
                headers={"apppublic": self.app_token, "appsecret": self.app_secret},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

        return FlouciPaymentStatus(
            payment_id=payment_id,
            status=data.get("result", {}).get("status", "PENDING"),
            amount=data.get("result", {}).get("amount", 0),
        )


flouci = FlouciClient()
