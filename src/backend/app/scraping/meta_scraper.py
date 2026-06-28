"""
Meta Ad Library scraper using Bright Data Web Scraper API.

The Meta Ad Library (facebook.com/ads/library) is publicly accessible.
We use Bright Data to reliably scrape it at scale, handling:
- Bot detection bypass
- Regional proxy rotation (MENA IPs)
- JavaScript rendering
- Rate limiting

Data flow:
  1. Bright Data scrapes Meta Ad Library pages
  2. We parse the HTML/JSON response into structured ad objects
  3. Media (images/videos) are downloaded and uploaded to R2
  4. Ads are indexed in Elasticsearch and stored in PostgreSQL
"""

import httpx
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field, asdict

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

# Popular ad categories/niches
NICHES = [
    "e-commerce",
    "fashion",
    "beauty",
    "food delivery",
    "real estate",
    "education",
    "fitness",
    "technology",
    "finance",
    "automotive",
]


@dataclass
class ScrapedAd:
    """Represents a single scraped ad from Meta Ad Library."""
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
        """Generate a unique hash for deduplication."""
        return hashlib.md5(f"{self.platform}:{self.ad_id}".encode()).hexdigest()


class MetaAdLibraryScraper:
    """
    Scrapes Meta Ad Library using Bright Data's infrastructure.

    Usage:
        scraper = MetaAdLibraryScraper(api_key="your_brightdata_key")
        ads = await scraper.scrape_country("TN", limit=100)
    """

    # Meta Ad Library base URL
    AD_LIBRARY_URL = "https://www.facebook.com/ads/library/"
    AD_LIBRARY_API = "https://www.facebook.com/ads/library/async/search_ads/"

    def __init__(self, api_key: str, zone: str = ""):
        self.api_key = api_key
        self.zone = zone
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,fr;q=0.7",
        }

    async def scrape_country(
        self,
        country: str,
        search_term: str = "",
        limit: int = 100,
        ad_type: str = "all",
    ) -> list[ScrapedAd]:
        """
        Scrape ads from Meta Ad Library for a specific country.

        Args:
            country: ISO country code (e.g., "TN", "SA")
            search_term: Optional keyword filter
            limit: Max ads to return
            ad_type: "all", "image", "video"

        Returns:
            List of ScrapedAd objects
        """
        logger.info(f"Scraping Meta ads for {country} (term='{search_term}', limit={limit})")

        ads = []

        # Build the scraping request for Bright Data
        # Using their Web Scraper API for structured extraction
        scrape_params = {
            "country": country,
            "search_term": search_term,
            "ad_type": ad_type,
            "active_status": "active",
            "limit": limit,
        }

        try:
            raw_ads = await self._fetch_via_brightdata(scrape_params)
            for raw in raw_ads:
                ad = self._parse_ad(raw, country)
                if ad and ad.ad_id:
                    ads.append(ad)

            logger.info(f"Scraped {len(ads)} ads for {country}")

        except Exception as e:
            logger.error(f"Error scraping {country}: {e}")

        return ads[:limit]

    async def _fetch_via_brightdata(self, params: dict) -> list[dict]:
        """
        Fetch ads using Bright Data's Web Scraper API.

        Bright Data handles:
        - Proxy rotation with country-specific residential IPs
        - JavaScript rendering (Meta Ad Library is React-based)
        - CAPTCHA solving
        - Rate limit management

        Docs: https://docs.brightdata.com/scraping-automation/web-scraper
        """
        # Method 1: Using Bright Data's Web Scraper API (recommended)
        # This sends a scraping job and returns structured data
        url = "https://api.brightdata.com/datasets/v3/trigger"

        payload = {
            "dataset_id": "gd_lyclm20il4r5helnj",  # Meta Ad Library dataset
            "endpoint": f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country={params['country']}&q={params.get('search_term', '')}",
            "format": "json",
            "limit_per_input": params.get("limit", 100),
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code == 200:
                snapshot_id = response.json().get("snapshot_id")
                # Poll for results
                return await self._poll_results(client, snapshot_id)
            else:
                logger.error(f"Bright Data API error: {response.status_code} - {response.text}")
                return []

    async def _poll_results(self, client: httpx.AsyncClient, snapshot_id: str) -> list[dict]:
        """Poll Bright Data for scraping results."""
        import asyncio

        url = f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        for attempt in range(30):  # Max 5 minutes
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return data
                status = data.get("status")
                if status == "ready":
                    return data.get("data", [])
                elif status == "failed":
                    logger.error(f"Snapshot {snapshot_id} failed")
                    return []

            await asyncio.sleep(10)

        logger.error(f"Timeout polling snapshot {snapshot_id}")
        return []

    def _parse_ad(self, raw: dict, country: str) -> Optional[ScrapedAd]:
        """Parse a raw Bright Data response into a ScrapedAd."""
        try:
            # Bright Data returns structured fields - map them
            ad = ScrapedAd(
                platform="meta",
                advertiser_name=raw.get("page_name", raw.get("advertiser_name", "")),
                advertiser_id=str(raw.get("page_id", raw.get("advertiser_id", ""))),
                ad_id=str(raw.get("ad_archive_id", raw.get("ad_id", ""))),
                country=country,
                language=self._detect_language(raw.get("ad_creative_bodies", [""])),
                ad_format=self._detect_format(raw),
                copy_text=self._extract_copy(raw),
                cta_text=raw.get("cta_text", raw.get("call_to_action", "")),
                landing_page=raw.get("ad_creative_link_captions", [None])[0]
                    if raw.get("ad_creative_link_captions") else
                    raw.get("landing_page", ""),
                media_urls=self._extract_media(raw),
                first_seen=raw.get("ad_delivery_start_time", raw.get("start_date", "")),
                last_seen=raw.get("ad_delivery_stop_time", datetime.now(timezone.utc).isoformat()),
                is_active=raw.get("is_active", True),
                metadata={
                    "impressions": raw.get("impressions", {}),
                    "spend": raw.get("spend", {}),
                    "demographic_distribution": raw.get("demographic_distribution", []),
                    "publisher_platforms": raw.get("publisher_platforms", []),
                },
            )
            return ad
        except Exception as e:
            logger.warning(f"Failed to parse ad: {e}")
            return None

    def _extract_copy(self, raw: dict) -> str:
        """Extract ad copy text from various possible fields."""
        bodies = raw.get("ad_creative_bodies", [])
        if bodies:
            return bodies[0] if isinstance(bodies, list) else str(bodies)
        return raw.get("body", raw.get("text", raw.get("copy", "")))

    def _extract_media(self, raw: dict) -> list[str]:
        """Extract media URLs (images/videos) from ad data."""
        urls = []

        # Check various media fields
        if raw.get("ad_snapshot_url"):
            urls.append(raw["ad_snapshot_url"])

        images = raw.get("images", raw.get("ad_creative_images", []))
        if isinstance(images, list):
            for img in images:
                if isinstance(img, dict):
                    urls.append(img.get("url", img.get("original_image_url", "")))
                elif isinstance(img, str):
                    urls.append(img)

        videos = raw.get("videos", raw.get("ad_creative_videos", []))
        if isinstance(videos, list):
            for vid in videos:
                if isinstance(vid, dict):
                    urls.append(vid.get("video_hd_url", vid.get("video_sd_url", "")))
                elif isinstance(vid, str):
                    urls.append(vid)

        return [u for u in urls if u]

    def _detect_format(self, raw: dict) -> str:
        """Detect ad format from media content."""
        if raw.get("videos") or raw.get("ad_creative_videos"):
            return "video"
        images = raw.get("images", raw.get("ad_creative_images", []))
        if isinstance(images, list) and len(images) > 1:
            return "carousel"
        return "image"

    def _detect_language(self, bodies: list) -> str:
        """Simple language detection for MENA content."""
        if not bodies:
            return "en"
        text = bodies[0] if isinstance(bodies, list) else str(bodies)

        # Check for Arabic characters
        arabic_chars = sum(1 for c in text if "؀" <= c <= "ۿ")
        if arabic_chars > len(text) * 0.3:
            return "ar"

        # Check for French indicators
        french_words = {"les", "des", "une", "est", "pour", "dans", "avec", "sur", "pas", "nous"}
        words = set(text.lower().split())
        if len(words & french_words) >= 2:
            return "fr"

        return "en"
