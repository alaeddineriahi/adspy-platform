"""One-time cleanup: collapse collated duplicate docs to one per creative per market.

Historic sweeps indexed every collated copy of a creative as its own doc
(30 copies of one Emily Turner ad, each with variant_count 90). The pipeline
now dedupes at index time (_dedupe_creatives); this removes what's already
there. Keeps, per (creative_key, country):
  1. any doc whose ad_id is referenced by a radar event or a saved ad
     (deleting those would 404 existing links), else
  2. the doc with the highest heat.

Run: venv/Scripts/python cleanup_dupes.py           (dry-run: reports only)
     venv/Scripts/python cleanup_dupes.py --apply   (actually deletes)
"""

import asyncio
import sys
from collections import defaultdict

from sqlalchemy import select

from app.core.database import async_session
from app.core.elasticsearch import get_es_client
from app.models.radar import RadarEvent
from app.models.saved import SavedAd


async def main() -> None:
    protected: set[str] = set()
    async with async_session() as db:
        for row in (await db.execute(select(RadarEvent.ad_id))).all():
            if row[0]:
                protected.add(row[0])
        for row in (await db.execute(select(SavedAd.ad_id))).all():
            if row[0]:
                protected.add(row[0])
    print(f"protected ad_ids (radar/saved): {len(protected)}")

    es = get_es_client()
    try:
        groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        resp = await es.search(index="ads", body={
            "size": 5000,
            "_source": ["creative_key", "country", "heat", "ad_id"],
            "query": {"match_all": {}},
        })
        for h in resp["hits"]["hits"]:
            s = h["_source"]
            groups[(s.get("creative_key") or h["_id"], s.get("country") or "")].append(
                {"id": h["_id"], "heat": s.get("heat") or 0}
            )

        to_delete: list[str] = []
        for _key, docs in groups.items():
            if len(docs) <= 1:
                continue
            keep_pool = [d for d in docs if d["id"] in protected] or docs
            keeper = max(keep_pool, key=lambda d: d["heat"])
            for d in docs:
                if d["id"] != keeper["id"] and d["id"] not in protected:
                    to_delete.append(d["id"])

        apply = "--apply" in sys.argv
        print(f"docs: {resp['hits']['total']['value']}, "
              f"creative groups: {len(groups)}, "
              f"{'deleting' if apply else 'WOULD delete (dry-run)'}: {len(to_delete)}")
        if not apply:
            return
        for i in range(0, len(to_delete), 500):
            ops = []
            for _id in to_delete[i:i + 500]:
                ops.append({"delete": {"_index": "ads", "_id": _id}})
            if ops:
                await es.bulk(operations=ops)
        if to_delete:
            await es.indices.refresh(index="ads")
        print("done.")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
