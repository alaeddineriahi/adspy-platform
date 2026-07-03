"""One-off: brand-intel migration.

1. put_mapping for the new fields (`countries`, `brand_live_ads`) — the index
   already exists, so the creation-time mapping never sees them, and dynamic
   mapping would guess `text` for countries (breaking term filters).
2. Backfill countries=[country] on every doc that doesn't have it yet.
"""

import asyncio

from app.core.elasticsearch import get_es_client


async def main():
    es = get_es_client()
    try:
        await es.indices.put_mapping(
            index="ads",
            properties={
                "countries": {"type": "keyword"},
                "brand_live_ads": {"type": "integer"},
            },
        )
        print("mapping updated")

        resp = await es.update_by_query(
            index="ads",
            body={
                "conflicts": "proceed",
                "query": {"bool": {"must_not": [{"exists": {"field": "countries"}}]}},
                "script": {"source": "ctx._source.countries = [ctx._source.country]"},
            },
            refresh=True,
        )
        print(f"countries backfilled on {resp.get('updated', 0)} docs "
              f"(failures={len(resp.get('failures', []))})")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
