"""One-off: backfill est_spend_min/max_usd + spend_basis on every doc."""

import asyncio

from app.core.elasticsearch import get_es_client
from app.ingestion.spend import estimate_spend


async def main():
    es = get_es_client()
    try:
        res = await es.search(
            index="ads",
            body={"query": {"match_all": {}}, "size": 3000,
                  "_source": ["country", "days_running", "variant_count"]},
        )
        hits = res["hits"]["hits"]
        ops: list[dict] = []
        for h in hits:
            s = h["_source"]
            lo, hi, basis = estimate_spend(
                s.get("country", ""), int(s.get("days_running") or 0),
                int(s.get("variant_count") or 1),
            )
            ops.append({"update": {"_index": "ads", "_id": h["_id"]}})
            ops.append({"doc": {"est_spend_min_usd": lo, "est_spend_max_usd": hi,
                                 "spend_basis": basis}})
        if ops:
            resp = await es.bulk(operations=ops, refresh=True)
            errors = [i for i in resp["items"] if i["update"].get("error")]
            print(f"updated={len(resp['items']) - len(errors)} errors={len(errors)}")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
