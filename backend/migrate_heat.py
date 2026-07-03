"""One-off: backfill heat/velocity/momentum on every existing doc.

New docs get these at index time (pipeline._build_doc); this recomputes them
for the whole catalog from stored fields so the new "printing money NOW"
sort works immediately.
"""

import asyncio

from app.core.elasticsearch import get_es_client, setup_index
from app.ingestion.scoring import compute_heat


async def main():
    es = get_es_client()
    try:
        await setup_index(es)  # ensure new field mappings exist
        res = await es.search(
            index="ads",
            body={"query": {"match_all": {}}, "size": 3000,
                  "_source": ["days_running", "variant_count", "ecom_signals",
                              "strong_commerce", "is_active", "thumbnail"]},
        )
        hits = res["hits"]["hits"]
        print(f"{len(hits)} docs to update")

        ops: list[dict] = []
        counts = {"hot": 0, "proven": 0, "steady": 0}
        for h in hits:
            s = h["_source"]
            heat, velocity, momentum = compute_heat(
                days=int(s.get("days_running") or 0),
                variants=int(s.get("variant_count") or 1),
                ecom_signals=int(s.get("ecom_signals") or 0),
                strong_commerce=bool(s.get("strong_commerce")),
                is_active=bool(s.get("is_active", True)),
                has_media=bool(s.get("thumbnail")),
            )
            counts[momentum] += 1
            ops.append({"update": {"_index": "ads", "_id": h["_id"]}})
            ops.append({"doc": {"heat": heat, "velocity": velocity, "momentum": momentum}})

        if ops:
            resp = await es.bulk(operations=ops, refresh=True)
            errors = [i for i in resp["items"] if i["update"].get("error")]
            print(f"updated={len(resp['items']) - len(errors)} errors={len(errors)}")
        print("momentum mix:", counts)
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
