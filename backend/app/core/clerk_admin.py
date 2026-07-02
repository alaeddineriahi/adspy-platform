"""
Clerk Backend API client — the source of truth for "who are our users."

We don't keep a local users table (Clerk owns identity); admin screens merge
this roster with our local billing/usage rows by Clerk user id. Also used to
promote/demote the `admin` role (public_metadata) and to mint impersonation
("actor") tokens for support.

Docs: https://clerk.com/docs/reference/backend-api
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("adspy.clerk_admin")

_BASE = "https://api.clerk.com/v1"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_BASE, headers=_headers(), timeout=10)


def _shape_user(u: dict) -> dict:
    emails = {e["id"]: e["email_address"] for e in u.get("email_addresses", [])}
    primary_email = emails.get(u.get("primary_email_address_id"), "")
    return {
        "id": u["id"],
        "email": primary_email or next(iter(emails.values()), ""),
        "name": " ".join(filter(None, [u.get("first_name"), u.get("last_name")])).strip() or None,
        "image_url": u.get("image_url"),
        "role": (u.get("public_metadata") or {}).get("role", "member"),
        "created_at": u.get("created_at"),  # epoch ms
        "last_sign_in_at": u.get("last_sign_in_at"),
        "banned": u.get("banned", False),  # Clerk's own account lock, separate from our UserFlag
    }


async def get_user(user_id: str) -> Optional[dict]:
    async with _client() as c:
        res = await c.get(f"/users/{user_id}")
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return _shape_user(res.json())


async def get_user_by_email(email: str) -> Optional[dict]:
    async with _client() as c:
        res = await c.get("/users", params={"email_address": [email]})
        res.raise_for_status()
        users = res.json()
        return _shape_user(users[0]) if users else None


async def list_users(limit: int = 50, offset: int = 0, query: Optional[str] = None) -> list[dict]:
    params: dict = {"limit": limit, "offset": offset, "order_by": "-created_at"}
    if query:
        params["query"] = query
    async with _client() as c:
        res = await c.get("/users", params=params)
        res.raise_for_status()
        return [_shape_user(u) for u in res.json()]


async def count_users(query: Optional[str] = None) -> int:
    params: dict = {}
    if query:
        params["query"] = query
    async with _client() as c:
        res = await c.get("/users/count", params=params)
        res.raise_for_status()
        return res.json().get("total_count", 0)


async def set_role(user_id: str, role: str) -> dict:
    """role: 'admin' or 'member'. Stored in Clerk public_metadata (visible client-side)."""
    async with _client() as c:
        res = await c.patch(f"/users/{user_id}/metadata", json={"public_metadata": {"role": role}})
        res.raise_for_status()
        return _shape_user(res.json())


async def create_impersonation_ticket(user_id: str, actor_user_id: str) -> str:
    """Mints a Clerk sign-in ticket for support impersonation.

    Redeemed client-side via signIn.create({ strategy: "ticket", ticket }).
    Clerk stamps the resulting session with `act.sub` = actor_user_id so it's
    auditable as "admin X acting as user Y" on Clerk's side too.
    """
    async with _client() as c:
        res = await c.post(
            "/actor_tokens",
            json={"user_id": user_id, "actor": {"sub": actor_user_id}, "expires_in_seconds": 300},
        )
        res.raise_for_status()
        return res.json()["token"]
