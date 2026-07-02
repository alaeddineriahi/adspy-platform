"""
Backend auth — verifies Clerk session JWTs.

The frontend sends `Authorization: Bearer <session token>` (from Clerk's
useAuth().getToken()). We verify the RS256 signature against the Clerk
instance's JWKS, check expiry + issuer, and return the `sub` claim (the Clerk
user id). This replaces the old unauthenticated X-User-Id header, which any
API client could spoof.

The Clerk issuer is derived from CLERK_PUBLISHABLE_KEY (`pk_test_<b64 domain>`),
so no extra .env entries are needed. If Clerk isn't configured at all AND
DEBUG=true, we fall back to the legacy X-User-Id header so local dev without
Clerk still works — never in production.
"""

import base64
import logging
from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger("adspy.auth")


@lru_cache(maxsize=1)
def clerk_issuer() -> str:
    """Clerk frontend-API origin, decoded from the publishable key."""
    pk = (getattr(settings, "CLERK_PUBLISHABLE_KEY", "") or "").strip()
    if not pk.startswith("pk_"):
        return ""
    try:
        b64 = pk.split("_", 2)[2]
        domain = base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode().rstrip("$")
        return f"https://{domain}"
    except Exception:  # noqa: BLE001 — malformed key just means "not configured"
        logger.warning("CLERK_PUBLISHABLE_KEY is set but couldn't be decoded.")
        return ""


@lru_cache(maxsize=1)
def _jwk_client():
    import jwt

    iss = clerk_issuer()
    if not iss:
        return None
    # Caches signing keys in-process; refetches JWKS when an unknown kid shows up.
    return jwt.PyJWKClient(f"{iss}/.well-known/jwks.json", cache_keys=True, lifespan=3600)


def _verify(token: str) -> str:
    """Verify a Clerk session JWT; returns the user id. Raises jwt exceptions."""
    import jwt

    signing_key = _jwk_client().get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=clerk_issuer(),
        options={"verify_aud": False},  # Clerk session tokens carry azp, not aud
        leeway=10,
    )
    # azp = the origin the token was minted for; reject tokens from foreign apps.
    azp = claims.get("azp")
    if azp and azp not in {settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:3001"}:
        raise jwt.InvalidTokenError(f"azp {azp!r} not allowed")
    sub = claims.get("sub")
    if not sub:
        raise jwt.InvalidTokenError("no sub claim")
    return sub


async def get_user_id(
    authorization: Optional[str] = Header(None),
    x_user_id: Optional[str] = Header(None),
) -> str:
    """FastAPI dependency: the verified Clerk user id of the caller (401 otherwise)."""
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()

    if token and _jwk_client() is not None:
        try:
            # PyJWKClient does blocking network I/O on a JWKS cache miss.
            return await run_in_threadpool(_verify, token)
        except Exception as e:  # noqa: BLE001 — any verification failure is a 401
            raise HTTPException(status_code=401, detail=f"Invalid session token: {e}")

    # Dev-only escape hatch: Clerk not configured at all + DEBUG.
    if _jwk_client() is None and settings.DEBUG:
        logger.warning("Auth in DEV-FALLBACK mode (Clerk not configured) — trusting X-User-Id.")
        return (x_user_id or "").strip() or "anonymous"

    raise HTTPException(status_code=401, detail="Missing bearer token")
