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
            "country": {"type": "keyword"},
            "language": {"type": "keyword"},
            "ad_format": {"type": "keyword"},
            "advertiser_id": {"type": "keyword"},
            "ad_id": {"type": "keyword"},
            "is_active": {"type": "boolean"},
            # Date fields
            "first_seen": {"type": "date"},
            "last_seen": {"type": "date"},
            "indexed_at": {"type": "date"},
            # Computed fields
            "days_running": {"type": "integer"},
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
        filter_clauses.append({"term": {"country": country}})
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
    if sort == "longest_running":
        sort_clause = [{"days_running": "desc"}, {"first_seen": "asc"}]
    elif sort == "newest":
        sort_clause = [{"first_seen": "desc"}]
    else:
        sort_clause = [{"_score": "desc"}, {"days_running": "desc"}]

    # Execute
    offset = (page - 1) * limit

    body = {
        "query": query,
        "sort": sort_clause,
        "from": offset,
        "size": limit,
        "_source": True,
    }

    result = await es.search(index="ads", body=body)

    hits = result["hits"]["hits"]
    total = result["hits"]["total"]["value"]

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
        filters.append({"term": {"country": country}})

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
