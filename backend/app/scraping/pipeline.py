"""
Ad processing pipeline.

Handles the full flow from raw scraped data to indexed, searchable ads:
  1. Deduplicate against existing ads
  2. Download media to Cloudflare R2
  3. Index in Elasticsearch
  4. Store in PostgreSQL
"""

import hashlib
import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional
from dataclasses import asdict

import httpx
import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

logger = logging.getLogger(__name__)


class MediaStorage:
    """Upload ad media (images/videos) to Cloudflare R2."""

    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            config=BotoConfig(signature_version="s3v4"),
            region_name="auto",
        )
        self.bucket = settings.R2_BUCKET
        self.public_url = settings.R2_PUBLIC_URL

    async def upload_media(self, url: str, ad_id: str, index: int = 0) -> Optional[str]:
        """Download media from source URL and upload to R2."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    return None

                content_type = resp.headers.get("content-type", "image/jpeg")
                ext = "jpg"
                if "video" in content_type:
                    ext = "mp4"
                elif "png" in content_type:
                    ext = "png"
                elif "webp" in content_type:
                    ext = "webp"

                key = f"ads/{ad_id}/{index}.{ext}"

                self.s3.put_object(
                    Bucket=self.bucket,
                    Key=key,
                    Body=resp.content,
                    ContentType=content_type,
                )

                return f"{self.public_url}/{key}"

        except Exception as e:
            logger.warning(f"Failed to upload media {url}: {e}")
            return None


class AdPipeline:
    """
    Process scraped ads through the full pipeline.

    Usage:
        pipeline = AdPipeline(es_client, db_session)
        stats = await pipeline.process(scraped_ads)
    """

    def __init__(self, es_client, db_session):
        self.es = es_client
        self.db = db_session
        self.storage = MediaStorage()
        self.stats = {"total": 0, "new": 0, "updated": 0, "errors": 0}

    async def process(self, ads: list) -> dict:
        """Process a batch of scraped ads."""
        self.stats = {"total": len(ads), "new": 0, "updated": 0, "errors": 0}

        for ad in ads:
            try:
                await self._process_single(ad)
            except Exception as e:
                logger.error(f"Error processing ad {ad.ad_id}: {e}")
                self.stats["errors"] += 1

        logger.info(
            f"Pipeline complete: {self.stats['new']} new, "
            f"{self.stats['updated']} updated, "
            f"{self.stats['errors']} errors out of {self.stats['total']} total"
        )
        return self.stats

    async def _process_single(self, ad):
        """Process a single ad through the pipeline."""

        # 1. Check if ad already exists (deduplicate)
        existing = await self._check_exists(ad.ad_id)

        if existing:
            # Update last_seen timestamp
            await self._update_last_seen(ad.ad_id)
            self.stats["updated"] += 1
            return

        # 2. Download and upload media to R2
        r2_urls = []
        for i, url in enumerate(ad.media_urls[:5]):  # Max 5 media per ad
            r2_url = await self.storage.upload_media(url, ad.ad_id, i)
            if r2_url:
                r2_urls.append(r2_url)

        ad.media_urls = r2_urls if r2_urls else ad.media_urls

        # 3. Index in Elasticsearch
        await self._index_to_es(ad)

        # 4. Store in PostgreSQL
        await self._store_to_db(ad)

        self.stats["new"] += 1

    async def _check_exists(self, ad_id: str) -> bool:
        """Check if ad already exists in the database."""
        try:
            result = await self.es.exists(index="ads", id=ad_id)
            return result
        except Exception:
            return False

    async def _update_last_seen(self, ad_id: str):
        """Update the last_seen timestamp for an existing ad."""
        try:
            await self.es.update(
                index="ads",
                id=ad_id,
                body={
                    "doc": {
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                        "is_active": True,
                    }
                },
            )
        except Exception as e:
            logger.warning(f"Failed to update last_seen for {ad_id}: {e}")

    async def _index_to_es(self, ad):
        """Index ad in Elasticsearch for search."""
        doc = asdict(ad)
        doc["days_running"] = self._calc_days_running(ad.first_seen)
        doc["indexed_at"] = datetime.now(timezone.utc).isoformat()

        await self.es.index(
            index="ads",
            id=ad.ad_id,
            body=doc,
        )

    async def _store_to_db(self, ad):
        """Store ad metadata in PostgreSQL."""
        # Uses SQLAlchemy async session
        from app.models.ad import Ad as AdModel

        db_ad = AdModel(
            platform=ad.platform,
            advertiser_name=ad.advertiser_name,
            advertiser_id=ad.advertiser_id,
            ad_id=ad.ad_id,
            country=ad.country,
            language=ad.language,
            ad_format=ad.ad_format,
            copy_text=ad.copy_text,
            cta_text=ad.cta_text,
            landing_page=ad.landing_page,
            media_urls=ad.media_urls,
            first_seen=ad.first_seen or datetime.now(timezone.utc),
            last_seen=ad.last_seen or datetime.now(timezone.utc),
            is_active=ad.is_active,
        )
        self.db.add(db_ad)
        await self.db.commit()

    def _calc_days_running(self, first_seen: str) -> int:
        """Calculate how many days an ad has been running."""
        if not first_seen:
            return 0
        try:
            start = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - start
            return max(0, delta.days)
        except Exception:
            return 0
