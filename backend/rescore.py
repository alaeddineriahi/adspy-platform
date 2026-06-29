"""
One-off: re-score the existing `ads` index under the current scoring rules.

The index was populated before the "printed money" re-weighting + the tighter
e-commerce gate, so it still holds stale scores and some non-ecom leakage
(long-running brand/app ads kept on days alone). This walks every stored doc,
reconstructs a RawAd from the indexed text/dates/scaling, re-runs `score_ad`,
then:
  • DELETES docs that no longer pass the keep gate (non-ecom / low-perf), and
  • REWRITES performance_score + is_ecommerce/strong_commerce/ecom_signals on
    the survivors so search ranks them by the new money proxy.

No re-scrape needed. Run:  venv/Scripts/python.exe rescore.py
"""

import asyncio
from datetime import datetime, timezone

from app.core.elasticsearch import get_es_client
from app.ingestion.scraper import RawAd
from app.ingestion.scoring import score_ad


def _raw_from_doc(doc: dict, now_ts: int) -> RawAd:
    days = int(doc.get("days_running") or 0)
    active = bool(doc.get("is_active", True))
    return RawAd(
        ad_id=str(doc.get("ad_id") or ""),
        page_id=str(doc.get("advertiser_id") or ""),
        page_name=doc.get("advertiser_name") or "Unknown",
        body_text=doc.get("copy_text") or "",
        cta_text=doc.get("cta_text") or "",
        link_url=doc.get("landing_page") or "",
        is_active=active,
        country=doc.get("country") or "",
        variant_count=int(doc.get("variant_count") or 1),
        # Re-derive timestamps so score_ad reproduces the stored days_running.
        start_ts=now_ts - days * 86400,
        end_ts=None if active else now_ts,
    )


async def main():
    es = get_es_client()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    scanned = updated = 0
    dropped = {"spam": 0, "marketplace": 0, "low_perf": 0}
    try:
        res = await es.search(index="ads", body={"query": {"match_all": {}}, "size": 2000})
        hits = res["hits"]["hits"]
        print(f"scanning {len(hits)} ads...")

        for h in hits:
            scanned += 1
            doc = h["_source"]
            _id = h["_id"]
            s = score_ad(_raw_from_doc(doc, now_ts), now_ts)

            if not s.keep:
                if s.spam_reason == "marketplace":
                    dropped["marketplace"] += 1
                elif s.spam_reason:
                    dropped["spam"] += 1
                else:
                    dropped["low_perf"] += 1
                await es.delete(index="ads", id=_id)
                continue

            doc.update(
                performance_score=s.score,
                variant_count=s.variant_count,
                is_ecommerce=s.is_ecommerce,
                strong_commerce=s.strong_commerce,
                ecom_signals=s.ecom_signals,
            )
            await es.index(index="ads", id=_id, document=doc)
            updated += 1

        await es.indices.refresh(index="ads")
        total = (await es.count(index="ads"))["count"]
        print(f"scanned:            {scanned}")
        print(f"kept & re-scored:   {updated}")
        print(f"dropped non-ecom/spam: {dropped['spam']}")
        print(f"dropped marketplace:   {dropped['marketplace']}")
        print(f"dropped low-perf:      {dropped['low_perf']}")
        print(f"index now holds:    {total} ads")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
