"""
One-off: add the `creative_key` field to the existing `ads` index and backfill it
so search can COLLAPSE near-duplicate creatives (same advertiser + opening copy)
into a single card instead of showing the same ad 3×.

Safe/idempotent. Run:  venv/Scripts/python.exe migrate_variants.py
"""

import asyncio

from app.core.elasticsearch import get_es_client
from app.ingestion.pipeline import creative_key


async def main():
    es = get_es_client()
    updated = skipped = 0
    try:
        # 1) Add the keyword field to the live mapping (adding a field is allowed).
        await es.indices.put_mapping(index="ads", body={"properties": {"creative_key": {"type": "keyword"}}})

        # 2) Backfill every doc that doesn't already have a matching key.
        res = await es.search(index="ads", body={"query": {"match_all": {}}, "size": 2000})
        hits = res["hits"]["hits"]
        print(f"scanning {len(hits)} ads...")

        for h in hits:
            doc = h["_source"]
            ck = creative_key(doc.get("advertiser_id", ""), doc.get("copy_text", ""))
            if doc.get("creative_key") == ck:
                skipped += 1
                continue
            await es.update(index="ads", id=h["_id"], body={"doc": {"creative_key": ck}})
            updated += 1

        await es.indices.refresh(index="ads")
        # Distinct creatives after collapse = cardinality of creative_key.
        agg = await es.search(index="ads", body={"size": 0, "aggs": {"g": {"cardinality": {"field": "creative_key"}}}})
        distinct = int(agg["aggregations"]["g"]["value"])
        total = (await es.count(index="ads"))["count"]
        print(f"backfilled creative_key: {updated} (already set: {skipped})")
        print(f"index holds {total} docs -> ~{distinct} distinct creatives after collapse")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
