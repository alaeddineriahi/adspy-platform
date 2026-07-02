"""
Credit metering — the single money lever (see PRICING.md).

Search and Brand Spy are ~free to serve and stay unmetered; every AI
generation (script, copy, analysis, media-buyer message) spends 1 credit.
Credits reset monthly (UTC calendar month). Limits come from the user's
active subscription; expired subscriptions silently degrade to Free.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import async_session
from app.models.billing import Subscription, CreditUsage

# Monthly AI credits per plan — keep in sync with PRICING.md §3 and /api/payments/plans.
PLAN_CREDITS = {"free": 10, "pro": 400, "agency": 1500}

SUBSCRIPTION_DAYS = 31  # one payment buys one month (+1 day grace)


def _period_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def effective_plan(sub) -> tuple[str, int]:
    """(plan, bonus) a Subscription row actually grants right now.

    Single source of truth for "is this sub live" — the admin backoffice must
    show the same plan the metering enforces, so expiry/status checks live
    here and nowhere else. Expired/cancelled/unknown → ("free", 0).
    """
    if (
        sub
        and sub.status == "active"
        and sub.plan in PLAN_CREDITS
        and (sub.current_period_end is None
             or sub.current_period_end > datetime.now(timezone.utc))
    ):
        return sub.plan, sub.credit_bonus or 0
    return "free", 0


async def _active_subscription(db, user_id: str) -> tuple[str, int]:
    sub = await db.scalar(select(Subscription).where(Subscription.user_id == user_id))
    return effective_plan(sub)


async def get_usage(user_id: str) -> dict:
    """Plan + credit numbers for /api/user/usage."""
    period = _period_now()
    async with async_session() as db:
        plan, bonus = await _active_subscription(db, user_id)
        used = await db.scalar(
            select(CreditUsage.used).where(
                CreditUsage.user_id == user_id, CreditUsage.period == period
            )
        ) or 0
    limit = PLAN_CREDITS[plan] + bonus
    return {
        "plan": plan,
        "period": period,
        "credits_used": used,
        "credits_limit": limit,
        "credits_remaining": max(0, limit - used),
    }


async def spend_credits(user_id: str, amount: int = 1) -> dict:
    """Atomically spend credits; raises 402 when the monthly allowance is gone."""
    period = _period_now()
    async with async_session() as db:
        plan, bonus = await _active_subscription(db, user_id)
        limit = PLAN_CREDITS[plan] + bonus

        # Ensure this month's row exists, then do a guarded atomic increment so
        # two concurrent requests can't overspend.
        await db.execute(
            pg_insert(CreditUsage)
            .values(user_id=user_id, period=period, used=0)
            .on_conflict_do_nothing(constraint="uq_credit_user_period")
        )
        res = await db.execute(
            update(CreditUsage)
            .where(
                CreditUsage.user_id == user_id,
                CreditUsage.period == period,
                CreditUsage.used + amount <= limit,
            )
            .values(used=CreditUsage.used + amount)
            .returning(CreditUsage.used)
        )
        row = res.first()
        await db.commit()

    if row is None:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "out_of_credits",
                "message": f"You've used all {limit} AI credits on the {plan} plan this month. "
                           "Upgrade to keep generating.",
                "plan": plan,
                "credits_limit": limit,
            },
        )
    used = row[0]
    return {"plan": plan, "credits_used": used, "credits_limit": limit,
            "credits_remaining": limit - used}


async def reset_usage(user_id: str) -> None:
    """Admin action: zero out the current month's credit usage."""
    period = _period_now()
    async with async_session() as db:
        await db.execute(
            pg_insert(CreditUsage)
            .values(user_id=user_id, period=period, used=0)
            .on_conflict_do_update(
                constraint="uq_credit_user_period",
                set_={"used": 0},
            )
        )
        await db.commit()


async def admin_override_subscription(
    user_id: str, plan: str, days: int = 31, credit_bonus: int = 0
) -> None:
    """Admin action: force a user's plan (comp, support fix) — not a real payment."""
    if plan not in PLAN_CREDITS:
        raise ValueError(f"Unknown plan: {plan}")
    period_end = (
        None if plan == "free" else datetime.now(timezone.utc) + timedelta(days=days)
    )
    async with async_session() as db:
        await db.execute(
            pg_insert(Subscription)
            .values(user_id=user_id, plan=plan, status="active",
                    current_period_end=period_end, credit_bonus=credit_bonus, is_comp=True)
            .on_conflict_do_update(
                index_elements=[Subscription.user_id],
                set_={"plan": plan, "status": "active", "current_period_end": period_end,
                      "credit_bonus": credit_bonus, "is_comp": True},
            )
        )
        await db.commit()


async def activate_subscription(user_id: str, plan: str, payment_ref: str | None = None) -> None:
    """Called by payment webhooks on a confirmed payment — upserts the subscription."""
    if plan not in PLAN_CREDITS or plan == "free":
        raise ValueError(f"Cannot activate plan {plan!r}")
    period_end = datetime.now(timezone.utc) + timedelta(days=SUBSCRIPTION_DAYS)
    async with async_session() as db:
        await db.execute(
            pg_insert(Subscription)
            .values(user_id=user_id, plan=plan, status="active",
                    current_period_end=period_end, payment_ref=payment_ref)
            .on_conflict_do_update(
                index_elements=[Subscription.user_id],
                set_={"plan": plan, "status": "active",
                      "current_period_end": period_end, "payment_ref": payment_ref},
            )
        )
        await db.commit()
