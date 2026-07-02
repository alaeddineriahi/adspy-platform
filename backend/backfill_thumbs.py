"""One-off: backfill thumbnails for docs the old pipeline left bare.

The old _build_doc only tried the FIRST image and set NO thumbnail when the
R2 mirror failed — leaving ~10% of the catalog with broken gray cards. For
each doc without a thumbnail, try mirroring each media_url (mirror_to_r2
itself rejects video content-types) until one sticks; report the rest.
"""

import asyncio

from app.core.elasticsearch import get_es_client
from app.ingestion.media import mirror_to_r2, r2_enabled


async def main():
    if not r2_enabled():
        print("R2 not configured — aborting.")
        return

    es = get_es_client()
    recovered = dead = 0
    try:
        res = await es.search(
            index="ads",
            body={
                "query": {"bool": {"must_not": [{"exists": {"field": "thumbnail"}}]}},
                "size": 500,
                "_source": ["media_urls", "advertiser_name"],
            },
        )
        hits = res["hits"]["hits"]
        print(f"{len(hits)} docs without thumbnails")

        sem = asyncio.Semaphore(8)

        async def fix(hit):
            nonlocal recovered, dead
            ad_id = hit["_id"]
            urls = (hit["_source"].get("media_urls") or [])[:4]
            async with sem:
                for url in urls:
                    r2_url = await mirror_to_r2(url, f"media/{ad_id}.jpg")
                    if r2_url:
                        await es.update(
                            index="ads", id=ad_id,
                            body={"doc": {"thumbnail": r2_url,
                                          "media_urls": [r2_url] + [u for u in urls if u != url]}},
                        )
                        recovered += 1
                        return
            dead += 1

        await asyncio.gather(*[fix(h) for h in hits])
        if recovered:
            await es.indices.refresh(index="ads")
        print(f"recovered={recovered} unrecoverable(expired)={dead}")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
