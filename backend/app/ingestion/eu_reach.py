"""
EU reach enrichment — real audience numbers for EU-delivered ads.

Under the DSA, Meta's OFFICIAL Ad Library API serves ALL ads delivered to
the EU (not just political) with `eu_total_reach` — actual unique users
reached. That's the only genuinely-published money signal available for
commercial ads anywhere, and our France sweep qualifies.

Runs after a sweep: for each EU country swept, query the official API with
the same search terms and join to our scraped docs by ad_archive_id.
Best-effort — silently skips when META_ACCESS_TOKEN is missing/expired
(logged once), so the pipeline never depends on it.
"""

import logging

import httpx

from app.core.config import settings
from app.ingestion.spend import estimate_spend

logger = logging.getLogger("adspy.eu_reach")

EU_COUNTRIES = {"FR"}  # extend when more EU markets join the sweep

_token_bad_logged = False


async def fetch_eu_reach(country: str, search_term: str, limit: int = 100) -> dict[str, int]:
    """{ad_archive_id: eu_total_reach} from the official API. Empty on any failure."""
    global _token_bad_logged
    token = getattr(settings, "META_ACCESS_TOKEN", "")
    if not token or country not in EU_COUNTRIES:
        return {}
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.get(
                f"https://graph.facebook.com/{settings.META_API_VERSION}/ads_archive",
                params={
                    "access_token": token,
                    "ad_reached_countries": f'["{country}"]',
                    "ad_type": "ALL",
                    "ad_active_status": "ALL",
                    "search_terms": search_term,
                    "fields": "id,eu_total_reach",
                    "limit": limit,
                },
            )
        data = resp.json()
        if "error" in data:
            code = data["error"].get("code")
            if not _token_bad_logged:
                _token_bad_logged = True
                logger.warning(
                    "EU reach enrichment disabled (API error %s): %s — refresh META_ACCESS_TOKEN "
                    "to light up real reach numbers for EU ads.",
                    code, data["error"].get("message", "")[:120],
                )
            return {}
        return {
            str(a["id"]): int(a["eu_total_reach"])
            for a in data.get("data", [])
            if a.get("eu_total_reach")
        }
    except Exception as e:  # noqa: BLE001 — enrichment must never break a sweep
        logger.warning("EU reach fetch failed for %s/'%s': %s", country, search_term, e)
        return {}


def apply_reach_to_doc(doc: dict, reach_by_id: dict[str, int]) -> None:
    """If we have real reach for this ad, upgrade its spend estimate in place."""
    reach = reach_by_id.get(str(doc.get("ad_id")))
    if not reach:
        return
    doc["eu_total_reach"] = reach
    lo, hi, basis = estimate_spend(
        doc.get("country", ""), int(doc.get("days_running") or 0),
        int(doc.get("variant_count") or 1), eu_total_reach=reach,
    )
    doc["est_spend_min_usd"] = lo
    doc["est_spend_max_usd"] = hi
    doc["spend_basis"] = basis
