"""
Meta Ad Library scraper using the official Facebook Ad Library API.

Free, no credit card required. Just needs a Facebook App access token.

Setup:
  1. Go to https://developers.facebook.com and create an app
  2. Get a User Access Token with `ads_read` permission
  3. Set META_ACCESS_TOKEN in your .env

API docs: https://www.facebook.com/ads/library/api/
"""

import httpx
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# MENA countries to scrape
MENA_COUNTRIES = {
    "TN": "Tunisia",
    "DZ": "Algeria",
    "MA": "Morocco",
    "EG": "Egypt",
    "SA": "Saudi Arabia",
    "AE": "United Arab Emirates",
    "KW": "Kuwait",
    "QA": "Qatar",
    "BH": "Bahrain",
    "OM": "Oman",
    "JO": "Jordan",
    "LB": "Lebanon",
}

# Official Ad Library API endpoint
AD_LIBRARY_API = "https://graph.facebook.com/v19.0/ads_archive"


@dataclass
class ScrapedAd:
    """Represents a single ad from Meta Ad Library."""
    platform: str = "meta"
    advertiser_name: str = ""
    advertiser_id: str = ""
    ad_id: str = ""
    country: str = ""
    language: str = ""
    ad_format: str = "image"  # image, video, carousel
    copy_text: str = ""
    cta_text: str = ""
    landing_page: str = ""
    media_urls: list = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    is_active: bool = True
    metadata: dict = field(default_factory=dict)

    @property
    def unique_hash(self) -> str:
        return hashlib.md5(f"{self.platform}:{self.ad_id}".encode()).hexdigest()


class MetaAdLibraryScraper:
    """
    Fetches ads from the official Meta Ad Library API.

    Usage:
        scraper = MetaAdLibraryScraper(access_token="your_token")
        ads = await scraper.scrape_country("TN", limit=100)
    """

    def __init__(self, access_token: str):
        self.access_token = access_token

    async def scrape_country(
        self,
        country: str,
        search_term: str = "",
        limit: int = 100,
        ad_type: str = "ALL",
    ) -> list[ScrapedAd]:
        """
        Fetch active ads for a country from the Meta Ad Library API.

        Args:
            country: ISO country code (e.g., "TN", "SA")
            search_term: Keyword filter (required by the API — use "" for broad search)
            limit: Max ads to return (API max per page is 500)
            ad_type: "ALL", "POLITICAL_AND_ISSUE_ADS"
        """
        logger.info(f"Fetching Meta ads for {country} (term='{search_term}', limit={limit})")

        ads = []
        params = {
            "access_token": self.access_token,
            "ad_reached_countries": f'["{country}"]',
            "ad_active_status": "ACTIVE",
            "ad_type": ad_type,
            "fields": (
                "id,page_id,page_name,ad_creative_bodies,"
                "ad_creative_link_captions,ad_creative_link_titles,"
                "ad_delivery_start_time,ad_delivery_stop_time,"
                "ad_snapshot_url,publisher_platforms,"
                "impressions,spend,demographic_distribution,"
                "languages,bylines"
            ),
            "limit": min(limit, 500),
        }

        if search_term:
            params["search_terms"] = search_term

        async with httpx.AsyncClient(timeout=30) as client:
            while len(ads) < limit:
                try:
                    resp = await client.get(AD_LIBRARY_API, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    logger.error(f"Meta API error for {country}: {e}")
                    break

                for raw in data.get("data", []):
                    ad = self._parse_ad(raw, country)
                    if ad and ad.ad_id:
                        ads.append(ad)

                # Follow pagination cursor
                next_cursor = data.get("paging", {}).get("cursors", {}).get("after")
                if not next_cursor or len(ads) >= limit:
                    break
                params["after"] = next_cursor

        logger.info(f"Fetched {len(ads)} ads for {country}")
        return ads[:limit]

    def _parse_ad(self, raw: dict, country: str) -> Optional[ScrapedAd]:
        try:
            bodies = raw.get("ad_creative_bodies") or []
            copy_text = bodies[0] if bodies else ""

            captions = raw.get("ad_creative_link_captions") or []
            landing_page = captions[0] if captions else ""

            langs = raw.get("languages") or []
            language = langs[0].lower() if langs else self._detect_language(copy_text)

            return ScrapedAd(
                platform="meta",
                advertiser_name=raw.get("page_name", ""),
                advertiser_id=str(raw.get("page_id", "")),
                ad_id=str(raw.get("id", "")),
                country=country,
                language=language,
                ad_format=self._detect_format(raw),
                copy_text=copy_text,
                cta_text="",
                landing_page=landing_page,
                media_urls=[raw["ad_snapshot_url"]] if raw.get("ad_snapshot_url") else [],
                first_seen=raw.get("ad_delivery_start_time", ""),
                last_seen=raw.get("ad_delivery_stop_time", datetime.now(timezone.utc).isoformat()),
                is_active=True,
                metadata={
                    "impressions": raw.get("impressions", {}),
                    "spend": raw.get("spend", {}),
                    "demographic_distribution": raw.get("demographic_distribution", []),
                    "publisher_platforms": raw.get("publisher_platforms", []),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to parse ad {raw.get('id')}: {e}")
            return None

    def _detect_format(self, raw: dict) -> str:
        bodies = raw.get("ad_creative_bodies") or []
        if len(bodies) > 1:
            return "carousel"
        snapshot = raw.get("ad_snapshot_url", "")
        if "video" in snapshot:
            return "video"
        return "image"

    def _detect_language(self, text: str) -> str:
        if not text:
            return "en"
        arabic_chars = sum(1 for c in text if "؀" <= c <= "ۿ")
        if arabic_chars > len(text) * 0.3:
            return "ar"
        french_words = {"les", "des", "une", "est", "pour", "dans", "avec", "sur", "pas", "nous"}
        if len(set(text.lower().split()) & french_words) >= 2:
            return "fr"
        return "en"
