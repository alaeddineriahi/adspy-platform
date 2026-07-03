"""
Mirror ad creatives to Cloudflare R2 so thumbnails persist.

Facebook CDN URLs (scontent.fbcdn.net/...?oh=…&oe=…) are signed and EXPIRE, and
they're hotlink-protected, so they don't render reliably in the app. At ingest we
download the creative once (while the URL is fresh) and re-host it on R2, which
gives a stable public URL. Best-effort: if R2 isn't configured or a fetch fails,
we fall back to the original URL.
"""

import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("adspy.media")

_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.facebook.com/",
    "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
}

_client = None  # cached boto3 S3 client for R2


def r2_enabled() -> bool:
    return bool(
        (getattr(settings, "R2_ACCESS_KEY", "") or "")
        and (getattr(settings, "R2_SECRET_KEY", "") or "")
        and (getattr(settings, "R2_ENDPOINT", "") or "")
        and (getattr(settings, "R2_PUBLIC_URL", "") or "")
    )


def _bucket() -> str:
    return getattr(settings, "R2_BUCKET", "") or getattr(settings, "R2_BUCKET_NAME", "") or "adspy-media"


def _get_client():
    global _client
    if _client is None:
        import boto3
        from botocore.config import Config

        _client = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
    return _client


def _put(key: str, data: bytes, content_type: str) -> None:
    _get_client().put_object(Bucket=_bucket(), Key=key, Body=data, ContentType=content_type)


async def mirror_to_r2(url: str, key: str) -> Optional[str]:
    """Download `url` and upload to R2 under `key`. Returns the public URL or None."""
    if not r2_enabled() or not url:
        return None
    try:
        # 10s is plenty for a healthy CDN fetch; dead/hotlink-blocked URLs would
        # otherwise burn the full timeout × 3 candidates × every doc in a batch.
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers=_FETCH_HEADERS)
        if resp.status_code != 200 or not resp.content:
            logger.info("media fetch %s -> HTTP %s", key, resp.status_code)
            return None
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        # Never store a video/audio as a thumbnail — it renders as a broken <img>.
        if ctype.startswith(("video/", "audio/")):
            logger.info("skip non-image media %s (%s)", key, ctype)
            return None
        if not ctype.startswith("image/"):
            ctype = "image/jpeg"  # unknown content-type → assume image
        await asyncio.to_thread(_put, key, resp.content, ctype)
        public = (getattr(settings, "R2_PUBLIC_URL", "") or "").rstrip("/")
        return f"{public}/{key}"
    except Exception as e:  # noqa: BLE001 — never let media issues break ingest
        # include the exception TYPE — httpx timeouts stringify to ""
        logger.warning("R2 mirror failed for %s: %s %s", key, type(e).__name__, e)
        return None
