"""
One-off: move already-mirrored thumbnails from the R2 key prefix "ads/" to
"media/" and rewrite the URLs stored in Elasticsearch.

Why: browser ad blockers block any URL path containing "/ads/", so the R2
thumbnail URLs (…r2.dev/ads/<id>.jpg) ERR_BLOCKED_BY_CLIENT and don't render.
This copies each object server-side (no re-download) to …/media/<id>.jpg and
updates the ad's thumbnail + media_urls. Old objects are left in place as a
harmless fallback.

Run:  venv/Scripts/python.exe rekey_media.py
"""

import asyncio

from app.core.config import settings
from app.core.elasticsearch import get_es_client
from app.ingestion.media import _bucket, _get_client, r2_enabled

PUBLIC = (getattr(settings, "R2_PUBLIC_URL", "") or "").rstrip("/")


def _rekey_url(url: str) -> str | None:
    """If `url` is one of our r2.dev /ads/ URLs, copy the object to /media/ and
    return the new URL. Otherwise return None (leave it alone)."""
    if not url or "r2.dev" not in url or "/ads/" not in url:
        return None
    if not url.startswith(PUBLIC + "/"):
        return None
    old_key = url[len(PUBLIC) + 1:]          # e.g. ads/123.jpg
    new_key = old_key.replace("ads/", "media/", 1)
    client, bucket = _get_client(), _bucket()
    try:
        client.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": old_key},
            Key=new_key,
        )
    except Exception as e:  # object may not exist (expired/never uploaded)
        print(f"  copy failed {old_key}: {e}")
        return None
    return f"{PUBLIC}/{new_key}"


async def main():
    if not r2_enabled():
        print("R2 not configured — nothing to do.")
        return
    es = get_es_client()
    scanned = moved = 0
    try:
        res = await es.search(index="ads", body={"query": {"match_all": {}}, "size": 2000})
        hits = res["hits"]["hits"]
        print(f"scanning {len(hits)} ads...")
        cache: dict[str, str] = {}

        for h in hits:
            scanned += 1
            doc = h["_source"]
            changed = False

            thumb = doc.get("thumbnail") or ""
            if thumb and "/ads/" in thumb and "r2.dev" in thumb:
                new = cache.get(thumb) or _rekey_url(thumb)
                if new:
                    cache[thumb] = new
                    doc["thumbnail"] = new
                    changed = True

            media = doc.get("media_urls") or []
            new_media = []
            for u in media:
                if u and "/ads/" in u and "r2.dev" in u:
                    nu = cache.get(u) or _rekey_url(u)
                    if nu:
                        cache[u] = nu
                        new_media.append(nu)
                        changed = True
                        continue
                new_media.append(u)
            if new_media != media:
                doc["media_urls"] = new_media

            if changed:
                await es.index(index="ads", id=h["_id"], document=doc)
                moved += 1

        await es.indices.refresh(index="ads")
        print(f"scanned: {scanned}")
        print(f"thumbnails re-keyed to /media/: {moved}")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
