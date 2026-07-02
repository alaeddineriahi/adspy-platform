"""
Admin backoffice API — every route behind require_admin (Clerk role="admin").

Clerk is the identity source of truth (no local users table); these routes
merge the Clerk roster with our local billing/usage/moderation rows by user
id. Every mutation writes an AuditLog row.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import OperationalError

from app.core import clerk_admin
from app.core.admin_auth import require_admin
from app.core.config import settings
from app.core.credits import (
    PLAN_CREDITS,
    admin_override_subscription,
    effective_plan,
    reset_usage,
)
from app.core.database import async_session, engine
from app.core.elasticsearch import get_es_client, get_top_brands as es_top_brands
from app.models.admin import AuditLog, UserFlag
from app.models.billing import Subscription, CreditUsage, PaymentIntent
from app.models.saved import SavedAd
from app.payments.konnect import PLAN_PRICES

logger = logging.getLogger("adspy.admin")
router = APIRouter()


async def _log(admin_id: str, action: str, target_user_id: Optional[str] = None,
                detail: Optional[str] = None) -> None:
    async with async_session() as db:
        db.add(AuditLog(admin_user_id=admin_id, action=action,
                         target_user_id=target_user_id, detail=detail))
        await db.commit()


@router.get("/me")
async def admin_me(uid: str = Depends(require_admin)):
    return {"is_admin": True, "user_id": uid}


# --- Overview -----------------------------------------------------------

@router.get("/overview")
async def overview(uid: str = Depends(require_admin)):
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    async with async_session() as db:
        # Resolve every sub through effective_plan so expired/cancelled rows
        # don't inflate MRR, and comps count as users but not as revenue.
        subs = (await db.execute(select(Subscription))).scalars().all()
        plan_counts: dict[str, int] = {}
        paid_subs = comp_subs = 0
        mrr_tnd = 0.0
        for s in subs:
            plan, _ = effective_plan(s)
            plan_counts[plan] = plan_counts.get(plan, 0) + 1
            if plan != "free":
                if s.is_comp:
                    comp_subs += 1
                else:
                    paid_subs += 1
                    mrr_tnd += PLAN_PRICES.get(plan, 0) / 1000

        credits_used_month = await db.scalar(
            select(func.sum(CreditUsage.used)).where(CreditUsage.period == period)
        ) or 0
        pending_payments = await db.scalar(
            select(func.count(PaymentIntent.id)).where(PaymentIntent.status == "pending")
        ) or 0

    es = get_es_client()
    try:
        total_ads = (await es.count(index="ads"))["count"]
        active_ads = (await es.count(index="ads", body={"query": {"term": {"is_active": True}}}))["count"]
        countries_agg = await es.search(
            index="ads", body={
                "size": 0,
                "aggs": {"countries": {"terms": {"field": "country", "size": 20}}},
            },
        )
        per_country = {
            b["key"]: b["doc_count"]
            for b in countries_agg["aggregations"]["countries"]["buckets"]
        }
    finally:
        await es.close()

    return {
        "revenue": {
            "mrr_tnd": round(mrr_tnd, 2),
            "paid_subscriptions": paid_subs,
            "comp_subscriptions": comp_subs,
            "plan_breakdown": {p: plan_counts.get(p, 0) for p in ("free", "pro", "agency")},
            "pending_payments": pending_payments,
        },
        "usage": {
            "ai_credits_used_this_month": int(credits_used_month),
        },
        "catalog": {
            "total_ads": total_ads,
            "active_ads": active_ads,
            "stale_ads": total_ads - active_ads,
            "per_country": per_country,
        },
    }


# --- Users ----------------------------------------------------------------

@router.get("/users")
async def list_users(
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uid: str = Depends(require_admin),
):
    roster = await clerk_admin.list_users(limit=limit, offset=offset, query=q)
    total = await clerk_admin.count_users(query=q)
    ids = [u["id"] for u in roster]
    if not ids:
        return {"results": [], "total": total}

    async with async_session() as db:
        subs = {
            s.user_id: s for s in (
                await db.execute(select(Subscription).where(Subscription.user_id.in_(ids)))
            ).scalars().all()
        }
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        usage_rows = (
            await db.execute(
                select(CreditUsage.user_id, CreditUsage.used).where(
                    CreditUsage.user_id.in_(ids), CreditUsage.period == period
                )
            )
        ).all()
        usage = {r[0]: r[1] for r in usage_rows}
        saved_counts = dict(
            (row[0], row[1]) for row in (
                await db.execute(
                    select(SavedAd.user_id, func.count(SavedAd.id))
                    .where(SavedAd.user_id.in_(ids))
                    .group_by(SavedAd.user_id)
                )
            ).all()
        )
        banned = set(
            r[0] for r in (
                await db.execute(select(UserFlag.user_id).where(
                    UserFlag.user_id.in_(ids), UserFlag.banned == True  # noqa: E712
                ))
            ).all()
        )

    results = []
    for u in roster:
        plan, bonus = effective_plan(subs.get(u["id"]))
        limit_c = PLAN_CREDITS[plan] + bonus
        results.append({
            **u,
            "plan": plan,
            "credits_used": usage.get(u["id"], 0),
            "credits_limit": limit_c,
            "saved_ads": saved_counts.get(u["id"], 0),
            "banned_in_app": u["id"] in banned,
        })
    return {"results": results, "total": total}


@router.get("/users/{user_id}")
async def user_detail(user_id: str, uid: str = Depends(require_admin)):
    clerk_user = await clerk_admin.get_user(user_id)
    if clerk_user is None:
        raise HTTPException(404, "User not found in Clerk")

    async with async_session() as db:
        sub = await db.scalar(select(Subscription).where(Subscription.user_id == user_id))
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        used = await db.scalar(
            select(CreditUsage.used).where(
                CreditUsage.user_id == user_id, CreditUsage.period == period
            )
        ) or 0
        saved_count = await db.scalar(
            select(func.count(SavedAd.id)).where(SavedAd.user_id == user_id)
        ) or 0
        flag = await db.scalar(select(UserFlag).where(UserFlag.user_id == user_id))
        payments = (
            await db.execute(
                select(PaymentIntent)
                .where(PaymentIntent.user_id == user_id)
                .order_by(PaymentIntent.created_at.desc())
                .limit(20)
            )
        ).scalars().all()
        audit = (
            await db.execute(
                select(AuditLog)
                .where(AuditLog.target_user_id == user_id)
                .order_by(AuditLog.created_at.desc())
                .limit(20)
            )
        ).scalars().all()

    plan, bonus = effective_plan(sub)
    limit_c = PLAN_CREDITS[plan] + bonus
    return {
        "user": clerk_user,
        "subscription": {
            "plan": plan,
            "status": sub.status if sub else "active",
            "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
            "credit_bonus": bonus,
            "is_comp": sub.is_comp if sub else False,
        },
        "usage": {"credits_used": used, "credits_limit": limit_c},
        "saved_ads": saved_count,
        "banned": bool(flag and flag.banned),
        "ban_reason": flag.ban_reason if flag else None,
        "payments": [
            {"payment_ref": p.payment_ref, "plan": p.plan, "provider": p.provider,
             "status": p.status, "created_at": p.created_at.isoformat()}
            for p in payments
        ],
        "audit_log": [
            {"action": a.action, "detail": a.detail, "admin_user_id": a.admin_user_id,
             "created_at": a.created_at.isoformat()}
            for a in audit
        ],
    }


class PlanOverrideRequest(BaseModel):
    plan: str  # free | pro | agency
    days: int = 31
    credit_bonus: int = 0


@router.post("/users/{user_id}/plan")
async def override_plan(user_id: str, req: PlanOverrideRequest, uid: str = Depends(require_admin)):
    if req.plan not in PLAN_CREDITS:
        raise HTTPException(400, f"Invalid plan. Choose: {list(PLAN_CREDITS.keys())}")
    await admin_override_subscription(user_id, req.plan, days=req.days, credit_bonus=req.credit_bonus)
    await _log(uid, "plan_override", user_id,
               f"plan={req.plan} days={req.days} bonus={req.credit_bonus}")
    return {"status": "ok"}


@router.post("/users/{user_id}/credits/reset")
async def credits_reset(user_id: str, uid: str = Depends(require_admin)):
    await reset_usage(user_id)
    await _log(uid, "credits_reset", user_id)
    return {"status": "ok"}


class BanRequest(BaseModel):
    banned: bool
    reason: Optional[str] = None


@router.post("/users/{user_id}/ban")
async def ban_user(user_id: str, req: BanRequest, uid: str = Depends(require_admin)):
    if user_id == uid and req.banned:
        raise HTTPException(400, "You can't ban yourself.")
    async with async_session() as db:
        await db.execute(
            pg_insert(UserFlag)
            .values(user_id=user_id, banned=req.banned, ban_reason=req.reason)
            .on_conflict_do_update(
                index_elements=[UserFlag.user_id],
                set_={"banned": req.banned, "ban_reason": req.reason},
            )
        )
        await db.commit()
    from app.core.account_flags import invalidate
    invalidate(user_id)  # take effect immediately, not after the auth cache TTL
    await _log(uid, "ban" if req.banned else "unban", user_id, req.reason)
    return {"status": "ok"}


class RoleRequest(BaseModel):
    role: str  # admin | member


@router.post("/users/{user_id}/role")
async def set_role(user_id: str, req: RoleRequest, uid: str = Depends(require_admin)):
    if req.role not in ("admin", "member"):
        raise HTTPException(400, "role must be 'admin' or 'member'")
    if user_id == uid and req.role == "member":
        raise HTTPException(400, "You can't demote yourself.")
    await clerk_admin.set_role(user_id, req.role)
    await _log(uid, "role_change", user_id, f"role={req.role}")
    return {"status": "ok"}


@router.post("/users/{user_id}/impersonate")
async def impersonate(user_id: str, uid: str = Depends(require_admin)):
    """Mints a short-lived Clerk sign-in ticket so support can see exactly what the user sees."""
    try:
        ticket = await clerk_admin.create_impersonation_ticket(user_id, actor_user_id=uid)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Clerk impersonation failed: {e}")
    await _log(uid, "impersonate", user_id)
    return {"ticket": ticket}


# --- Billing ----------------------------------------------------------------

@router.get("/billing")
async def billing(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    uid: str = Depends(require_admin),
):
    async with async_session() as db:
        sub_q = select(Subscription).order_by(Subscription.updated_at.desc()).limit(limit)
        if status:
            sub_q = sub_q.where(Subscription.status == status)
        subs = (await db.execute(sub_q)).scalars().all()

        pay_q = select(PaymentIntent).order_by(PaymentIntent.created_at.desc()).limit(limit)
        payments = (await db.execute(pay_q)).scalars().all()

    return {
        "subscriptions": [
            {"user_id": s.user_id, "plan": s.plan, "status": s.status,
             "current_period_end": s.current_period_end.isoformat() if s.current_period_end else None,
             "credit_bonus": s.credit_bonus, "is_comp": s.is_comp,
             "payment_ref": s.payment_ref}
            for s in subs
        ],
        "payments": [
            {"payment_ref": p.payment_ref, "user_id": p.user_id, "plan": p.plan,
             "provider": p.provider, "status": p.status, "created_at": p.created_at.isoformat()}
            for p in payments
        ],
    }


# --- Catalog / moderation ----------------------------------------------------

@router.get("/catalog/overview")
async def catalog_overview(uid: str = Depends(require_admin)):
    es = get_es_client()
    try:
        total = (await es.count(index="ads"))["count"]
        agg = await es.search(
            index="ads", body={
                "size": 0,
                "aggs": {
                    "by_country": {"terms": {"field": "country", "size": 20}},
                    "active": {"filter": {"term": {"is_active": True}}},
                    "by_format": {"terms": {"field": "ad_format", "size": 10}},
                },
            },
        )
        top_brands = await es_top_brands(es, limit=10)
    finally:
        await es.close()

    return {
        "total_ads": total,
        "active_ads": agg["aggregations"]["active"]["doc_count"],
        "by_country": {b["key"]: b["doc_count"] for b in agg["aggregations"]["by_country"]["buckets"]},
        "by_format": {b["key"]: b["doc_count"] for b in agg["aggregations"]["by_format"]["buckets"]},
        "top_brands": top_brands["results"],
    }


@router.get("/catalog/ads")
async def browse_ads(
    q: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    uid: str = Depends(require_admin),
):
    filters = []
    if country:
        filters.append({"term": {"country": country}})
    query = {"bool": {"must": [{"match": {"copy_text": q}}] if q else [{"match_all": {}}],
                       "filter": filters}}
    es = get_es_client()
    try:
        result = await es.search(
            index="ads",
            body={"query": query, "sort": [{"indexed_at": "desc"}], "from": offset, "size": limit},
        )
    finally:
        await es.close()
    hits = result["hits"]["hits"]
    return {
        "results": [{**h["_source"], "id": h["_id"]} for h in hits],
        "total": result["hits"]["total"]["value"],
    }


@router.delete("/catalog/ads/{ad_id}")
async def delete_ad(ad_id: str, uid: str = Depends(require_admin)):
    es = get_es_client()
    try:
        try:
            await es.delete(index="ads", id=ad_id)
        except Exception:
            raise HTTPException(404, "Ad not found")
        await es.indices.refresh(index="ads")
    finally:
        await es.close()
    await _log(uid, "ad_delete", detail=f"ad_id={ad_id}")
    return {"status": "deleted", "ad_id": ad_id}


# --- Audit log ----------------------------------------------------------------

@router.get("/audit")
async def audit_log(
    user_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    uid: str = Depends(require_admin),
):
    async with async_session() as db:
        q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if user_id:
            q = q.where(
                (AuditLog.target_user_id == user_id) | (AuditLog.admin_user_id == user_id)
            )
        rows = (await db.execute(q)).scalars().all()
    return {
        "results": [
            {"admin_user_id": a.admin_user_id, "action": a.action,
             "target_user_id": a.target_user_id, "detail": a.detail,
             "created_at": a.created_at.isoformat()}
            for a in rows
        ]
    }


# --- System health ----------------------------------------------------------------

async def _tcp_reachable(url: str, timeout: float = 1.5) -> bool:
    parsed = urlparse(url)
    host, port = parsed.hostname, parsed.port
    if not host or not port:
        return False
    try:
        fut = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


@router.get("/health")
async def system_health(uid: str = Depends(require_admin)):
    checks = {}

    es = get_es_client()
    try:
        h = await es.cluster.health()
        checks["elasticsearch"] = {"ok": h["status"] in ("green", "yellow"), "status": h["status"]}
    except Exception as e:  # noqa: BLE001
        checks["elasticsearch"] = {"ok": False, "status": str(e)}
    finally:
        await es.close()

    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        checks["postgres"] = {"ok": True}
    except OperationalError as e:
        checks["postgres"] = {"ok": False, "status": str(e)}

    checks["redis"] = {"ok": await _tcp_reachable(settings.REDIS_URL), "status": "tcp reachability only — no client wired"}

    from app.ingestion.session import session_available, describe_source
    from app.ingestion.pipeline import LAST_RUN

    checks["facebook_session"] = {
        "ok": await session_available(),
        "status": describe_source(),
    }
    checks["last_ingestion"] = {
        "status": LAST_RUN.get("status"),
        "finished_at": LAST_RUN.get("finished_at"),
        "alert": LAST_RUN.get("alert"),
    }

    return checks
