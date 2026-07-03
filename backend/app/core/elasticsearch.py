"""
Elasticsearch client and index management.

Index mapping optimized for ad search:
- Full-text search on copy_text, advertiser_name (Arabic/French/English)
- Faceted filters on platform, country, language, ad_format
- Sorting by days_running (proxy for profitability), first_seen
"""

from elasticsearch import AsyncElasticsearch
from app.core.config import settings

# Index mapping for ads
ADS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                # Custom analyzer for Arabic + French + English text
                "multilingual": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "arabic_normalization",
                        "asciifolding",
                    ],
                },
                "domain_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase"],
                    "char_filter": ["domain_strip"],
                },
            },
            "char_filter": {
                "domain_strip": {
                    "type": "pattern_replace",
                    "pattern": "(https?://)?(www\\.)?",
                    "replacement": "",
                },
            },
        },
    },
    "mappings": {
        "properties": {
            # Searchable text fields
            "copy_text": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 512}},
            },
            "advertiser_name": {
                "type": "text",
                "analyzer": "multilingual",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "cta_text": {"type": "keyword"},
            "landing_page": {
                "type": "text",
                "analyzer": "domain_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            # Filter / facet fields
            "platform": {"type": "keyword"},
            "country": {"type": "keyword"},        # first market we saw the ad in
            "countries": {"type": "keyword"},      # every market sweeps have seen it in
            "brand_live_ads": {"type": "integer"}, # advertiser's TOTAL live ads (deep-dive)
            "language": {"type": "keyword"},
            "ad_format": {"type": "keyword"},
            "advertiser_id": {"type": "keyword"},
            "ad_id": {"type": "keyword"},
            "creative_key": {"type": "keyword"},
            "is_active": {"type": "boolean"},
            # Date fields
            "first_seen": {"type": "date"},
            "last_seen": {"type": "date"},
            "indexed_at": {"type": "date"},
            # Computed fields
            "days_running": {"type": "integer"},
            "variant_count": {"type": "integer"},
            "performance_score": {"type": "float"},
            "heat": {"type": "float"},          # "printing money NOW" composite
            "velocity": {"type": "float"},      # variants per 30d of age
            "momentum": {"type": "keyword"},    # hot | proven | steady
            "est_spend_min_usd": {"type": "integer"},
            "est_spend_max_usd": {"type": "integer"},
            "spend_basis": {"type": "keyword"},   # heuristic | reach
            "eu_total_reach": {"type": "long"},   # real, DSA-published (EU ads)
            "ecom_signals": {"type": "integer"},
            "is_ecommerce": {"type": "boolean"},
            "strong_commerce": {"type": "boolean"},
            # Media
            "media_urls": {"type": "keyword", "index": False},
            # Nested metadata
            "metadata": {"type": "object", "enabled": False},
        }
    },
}


def get_es_client() -> AsyncElasticsearch:
    """Get async Elasticsearch client."""
    return AsyncElasticsearch(
        hosts=[settings.ELASTICSEARCH_URL],
        request_timeout=30,
    )


async def setup_index(es: AsyncElasticsearch):
    """Create the ads index if it doesn't exist."""
    exists = await es.indices.exists(index="ads")
    if not exists:
        await es.indices.create(index="ads", body=ADS_INDEX_MAPPING)
        print("Created 'ads' index")
    else:
        print("'ads' index already exists")


async def search_ads(
    es: AsyncElasticsearch,
    q: str = "",
    platform: str = None,
    country: str = None,
    language: str = None,
    ad_format: str = None,
    is_active: bool = None,
    sort: str = "newest",
    page: int = 1,
    limit: int = 20,
) -> dict:
    """
    Search ads with full-text query and filters.

    Returns: {"results": [...], "total": int, "page": int}
    """
    must = []
    filter_clauses = []

    # Full-text search across copy, advertiser name, landing page
    if q:
        must.append({
            "multi_match": {
                "query": q,
                "fields": [
                    "copy_text^2",
                    "advertiser_name^3",
                    "landing_page",
                    "cta_text",
                ],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        })

    # Filters
    if platform:
        filter_clauses.append({"term": {"platform": platform}})
    if country:
        # `countries` covers every market the ad was seen in (backfilled on all
        # docs); a pan-GCC ad now matches SA *and* KW instead of only the last
        # sweep that touched it.
        filter_clauses.append({"term": {"countries": country}})
    if language:
        filter_clauses.append({"term": {"language": language}})
    if ad_format:
        filter_clauses.append({"term": {"ad_format": ad_format}})
    if is_active is not None:
        filter_clauses.append({"term": {"is_active": is_active}})

    # Build query
    query = {"bool": {}}
    if must:
        query["bool"]["must"] = must
    if filter_clauses:
        query["bool"]["filter"] = filter_clauses
    if not must and not filter_clauses:
        query = {"match_all": {}}

    # Sort
    sort_clause = []
    if sort == "best_performing":
        # "Printing money NOW": heat leads (velocity-weighted, media-aware),
        # lifetime score + raw scaling break ties. Missing fields sort last.
        sort_clause = [
            {"heat": {"order": "desc", "missing": "_last"}},
            {"performance_score": {"order": "desc", "missing": "_last"}},
            {"variant_count": {"order": "desc", "missing": "_last"}},
        ]
    elif sort == "longest_running":
        sort_clause = [{"days_running": "desc"}, {"first_seen": "asc"}]
    elif sort == "newest":
        sort_clause = [{"first_seen": "desc"}]
    else:
        sort_clause = [{"_score": "desc"}, {"performance_score": {"order": "desc", "missing": "_last"}}]

    # Execute
    offset = (page - 1) * limit

    body = {
        "query": query,
        "sort": sort_clause,
        "from": offset,
        "size": limit,
        "_source": True,
        # Collapse near-duplicate creatives (same advertiser + copy) into one card
        # so the same ad doesn't appear 3×. The kept hit carries variant_count.
        "collapse": {"field": "creative_key"},
        # Distinct-creative count so pagination reflects cards shown, not raw docs.
        "aggs": {"groups": {"cardinality": {"field": "creative_key"}}},
    }

    result = await es.search(index="ads", body=body)

    hits = result["hits"]["hits"]
    doc_total = result["hits"]["total"]["value"]
    total = int(result.get("aggregations", {}).get("groups", {}).get("value", doc_total))

    return {
        "results": [
            {**hit["_source"], "id": hit["_id"], "score": hit.get("_score")}
            for hit in hits
        ],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


async def get_brand_ads(
    es: AsyncElasticsearch,
    advertiser_id: str = None,
    advertiser_name: str = None,
    page: int = 1,
    limit: int = 50,
) -> dict:
    """Get all ads for a specific brand/advertiser."""
    if advertiser_id:
        query = {"term": {"advertiser_id": advertiser_id}}
    elif advertiser_name:
        query = {"match": {"advertiser_name": {"query": advertiser_name, "fuzziness": "AUTO"}}}
    else:
        return {"results": [], "total": 0}

    body = {
        "query": query,
        "sort": [{"first_seen": "desc"}],
        "from": (page - 1) * limit,
        "size": limit,
    }

    result = await es.search(index="ads", body=body)
    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]

    return {
        "results": [{**h["_source"], "id": h["_id"]} for h in hits],
        "total": total,
        "brand": advertiser_name or advertiser_id,
        "page": page,
    }


async def get_top_brands(
    es: AsyncElasticsearch,
    q: str = None,
    country: str = None,
    min_live_ads: int = 0,
    limit: int = 24,
) -> dict:
    """Rank advertisers by how much money they look to be printing.

    Our index already holds only winning e-commerce ads, so we aggregate each
    advertiser's footprint inside it:
      • total_variants  — Σ variant_count = total creative scaling (the strongest
                          free "they're pouring budget into winners" signal),
      • winning_ads     — how many distinct winners they're running,
      • top_score       — their single best ad's "printed money" score,
      • max_days        — longest a creative has stayed live,
      • live_ads        — the brand's REAL total live-ad count in the Ad Library
                          (from the deep-dive; 0 = not yet deep-dived).
    Brands are ordered by total scaling (the money proxy). Pass `q` to filter by
    name, `country` to scope to one market, `min_live_ads` for the "brands
    running 50+ ads" style quality cut.
    """
    if q:
        base_query = {"match": {"advertiser_name": {"query": q, "fuzziness": "AUTO"}}}
    else:
        base_query = {"match_all": {}}
    if country:
        base_query = {"bool": {"must": [base_query], "filter": [{"term": {"countries": country}}]}}

    # min_live_ads filters BUCKETS, not docs, so over-fetch then cut in Python.
    bucket_size = limit * 4 if min_live_ads else limit
    body = {
        "size": 0,
        "query": base_query,
        "aggs": {
            "brands": {
                "terms": {
                    "field": "advertiser_name.keyword",
                    "size": bucket_size,
                    "order": {"total_variants": "desc"},
                },
                "aggs": {
                    "advertiser_id": {"terms": {"field": "advertiser_id", "size": 1}},
                    "active": {"filter": {"term": {"is_active": True}}},
                    "countries": {"terms": {"field": "countries", "size": 10}},
                    "total_variants": {"sum": {"field": "variant_count"}},
                    "top_score": {"max": {"field": "performance_score"}},
                    "max_days": {"max": {"field": "days_running"}},
                    "live_ads": {"max": {"field": "brand_live_ads"}},
                },
            }
        },
    }
    result = await es.search(index="ads", body=body)
    buckets = result.get("aggregations", {}).get("brands", {}).get("buckets", [])
    brands = [
        {
            "advertiser_name": b["key"],
            "advertiser_id": (
                b["advertiser_id"]["buckets"][0]["key"]
                if b["advertiser_id"]["buckets"] else None
            ),
            "total_ads": b["doc_count"],
            "active_ads": b["active"]["doc_count"],
            "countries": [c["key"] for c in b["countries"]["buckets"]],
            "total_variants": int(b["total_variants"]["value"] or 0),
            "top_score": round(b["top_score"]["value"] or 0, 1),
            "max_days": int(b["max_days"]["value"] or 0),
            "live_ads": int(b["live_ads"]["value"] or 0),
        }
        for b in buckets
    ]
    if min_live_ads:
        brands = [b for b in brands if b["live_ads"] >= min_live_ads][:limit]
    return {"results": brands, "total": len(brands)}


async def get_trending_ads(
    es: AsyncElasticsearch,
    country: str = None,
    limit: int = 20,
) -> dict:
    """Get longest-running ads (proxy for profitable/winning ads)."""
    filters = [
        {"term": {"is_active": True}},
        {"range": {"days_running": {"gte": 14}}},
    ]
    if country:
        filters.append({"term": {"countries": country}})

    body = {
        "query": {"bool": {"filter": filters}},
        "sort": [{"days_running": "desc"}],
        "size": limit,
    }

    result = await es.search(index="ads", body=body)
    hits = result["hits"]["hits"]

    return {
        "results": [{**h["_source"], "id": h["_id"]} for h in hits],
        "total": result["hits"]["total"]["value"],
    }
