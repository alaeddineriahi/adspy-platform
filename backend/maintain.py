"""
One-off maintenance:
  1. Purge seed/sample ads (anything not from the live scraper) so the library
     is 100% real scraped winners.
  2. Backfill R2 thumbnails for scraped ads that still point at Facebook CDN URLs
     (mirrors them to R2 if the signed URL hasn't expired yet).

Run:  venv/Scripts/python.exe maintain.py
"""

import asyncio

from app.core.elasticsearch import get_es_client
from app.ingestion.media import mirror_to_r2, r2_enabled


async def main():
    es = get_es_client()
    deleted = kept = backfilled = failed = 0
    try:
        res = await es.search(index="ads", body={"query": {"match_all": {}}, "size": 2000})
        hits = res["hits"]["hits"]
        print(f"scanning {len(hits)} ads...")

        for h in hits:
            doc = h["_source"]
            _id = h["_id"]

            # 1) purge non-scraped (seed.py + seed_real.py) records
            if doc.get("source") != "ad_library_scrape":
                await es.delete(index="ads", id=_id)
                deleted += 1
                continue
            kept += 1

            # 2) backfill R2 thumbnail if it's still an FB CDN url
            thumb = doc.get("thumbnail") or ""
            if not r2_enabled() or "r2.dev" in thumb:
                continue
            media = doc.get("media_urls") or []
            src_url = next((u for u in media if u and "r2.dev" not in u), None)
            if not src_url:
                continue
            r2 = await mirror_to_r2(src_url, f"ads/{doc.get('ad_id', _id)}.jpg")
            if r2:
                doc["thumbnail"] = r2
                doc["media_urls"] = [r2] + [u for u in media if u != src_url]
                await es.index(index="ads", id=_id, document=doc)
                backfilled += 1
            else:
                failed += 1  # FB url likely expired — will refresh on next scrape

        await es.indices.refresh(index="ads")
        total = (await es.count(index="ads"))["count"]
        print(f"deleted seed ads: {deleted}")
        print(f"kept scraped ads: {kept}")
        print(f"R2 thumbnails backfilled: {backfilled} (failed/expired: {failed})")
        print(f"index now holds {total} ads")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
