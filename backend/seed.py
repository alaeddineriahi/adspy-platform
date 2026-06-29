"""
Seed the Elasticsearch 'ads' index with sample MENA ads so search/trending
return real results during local development.

Run:  venv/Scripts/python.exe seed.py
"""

import asyncio
from datetime import datetime, timezone, timedelta

from app.core.elasticsearch import get_es_client, setup_index


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()


SAMPLE_ADS = [
    {
        "ad_id": "meta_tn_001",
        "platform": "meta",
        "advertiser_name": "Tunisie Telecom",
        "advertiser_id": "adv_tt",
        "country": "TN",
        "language": "fr",
        "ad_format": "video",
        "copy_text": "Profitez de la 4G+ illimitée tout l'été ! Forfait spécial à partir de 25 DT. Abonnez-vous maintenant.",
        "cta_text": "Souscrire",
        "landing_page": "https://tunisietelecom.tn/4g",
        "media_urls": ["https://picsum.photos/seed/tt/640/360"],
        "first_seen": _days_ago(45),
        "is_active": True,
    },
    {
        "ad_id": "meta_tn_002",
        "platform": "meta",
        "advertiser_name": "Jumia Tunisie",
        "advertiser_id": "adv_jumia",
        "country": "TN",
        "language": "ar",
        "ad_format": "carousel",
        "copy_text": "تخفيضات الصيف الكبرى! خصومات تصل إلى 70% على الإلكترونيات والموضة. توصيل مجاني لكامل تونس.",
        "cta_text": "تسوق الآن",
        "landing_page": "https://jumia.com.tn/sale",
        "media_urls": ["https://picsum.photos/seed/jumia/640/360"],
        "first_seen": _days_ago(30),
        "is_active": True,
    },
    {
        "ad_id": "tiktok_ae_003",
        "platform": "tiktok",
        "advertiser_name": "Noon UAE",
        "advertiser_id": "adv_noon",
        "country": "AE",
        "language": "en",
        "ad_format": "video",
        "copy_text": "Stop scrolling! Get same-day delivery on 1M+ products. Use code NOON20 for 20% off your first order.",
        "cta_text": "Shop Now",
        "landing_page": "https://noon.com/uae",
        "media_urls": ["https://picsum.photos/seed/noon/640/360"],
        "first_seen": _days_ago(60),
        "is_active": True,
    },
    {
        "ad_id": "meta_eg_004",
        "platform": "meta",
        "advertiser_name": "Vodafone Egypt",
        "advertiser_id": "adv_voda",
        "country": "EG",
        "language": "ar",
        "ad_format": "image",
        "copy_text": "باقة الإنترنت الجديدة من فودافون: 100 جيجا بسعر لا يُصدق. اشترك دلوقتي عبر تطبيق Ana Vodafone.",
        "cta_text": "اشترك",
        "landing_page": "https://vodafone.com.eg",
        "media_urls": ["https://picsum.photos/seed/voda/640/360"],
        "first_seen": _days_ago(12),
        "is_active": True,
    },
    {
        "ad_id": "meta_sa_005",
        "platform": "meta",
        "advertiser_name": "Almosafer",
        "advertiser_id": "adv_almosafer",
        "country": "SA",
        "language": "ar",
        "ad_format": "video",
        "copy_text": "احجز رحلتك القادمة بأفضل الأسعار. عروض حصرية على الفنادق والطيران داخل المملكة وخارجها.",
        "cta_text": "احجز الآن",
        "landing_page": "https://almosafer.com",
        "media_urls": ["https://picsum.photos/seed/almosafer/640/360"],
        "first_seen": _days_ago(90),
        "is_active": True,
    },
    {
        "ad_id": "tiktok_tn_006",
        "platform": "tiktok",
        "advertiser_name": "GlowUp Cosmetics",
        "advertiser_id": "adv_glowup",
        "country": "TN",
        "language": "fr",
        "ad_format": "video",
        "copy_text": "Le sérum vitamine C qui fait fondre la Tunisie ! Résultats visibles en 7 jours. Stock limité.",
        "cta_text": "Commander",
        "landing_page": "https://glowup.tn",
        "media_urls": ["https://picsum.photos/seed/glowup/640/360"],
        "first_seen": _days_ago(8),
        "is_active": True,
    },
    {
        "ad_id": "meta_ma_007",
        "platform": "meta",
        "advertiser_name": "Inwi Maroc",
        "advertiser_id": "adv_inwi",
        "country": "MA",
        "language": "fr",
        "ad_format": "image",
        "copy_text": "Passez à la fibre Inwi : débit ultra rapide à petit prix. Installation gratuite ce mois-ci.",
        "cta_text": "Découvrir",
        "landing_page": "https://inwi.ma/fibre",
        "media_urls": ["https://picsum.photos/seed/inwi/640/360"],
        "first_seen": _days_ago(22),
        "is_active": True,
    },
    {
        "ad_id": "meta_tn_008",
        "platform": "meta",
        "advertiser_name": "Délice Danone",
        "advertiser_id": "adv_delice",
        "country": "TN",
        "language": "ar",
        "ad_format": "carousel",
        "copy_text": "نكهات جديدة من ديليس! جرّب تشكيلتنا الصيفية المنعشة المتوفرة الآن في كل المتاجر.",
        "cta_text": "اكتشف",
        "landing_page": "https://delice.tn",
        "media_urls": ["https://picsum.photos/seed/delice/640/360"],
        "first_seen": _days_ago(120),
        "is_active": True,
    },
]


def _calc_days_running(first_seen: str) -> int:
    start = datetime.fromisoformat(first_seen)
    return max(0, (datetime.now(timezone.utc) - start).days)


async def main():
    es = get_es_client()
    try:
        await setup_index(es)
        for ad in SAMPLE_ADS:
            doc = {
                **ad,
                "last_seen": datetime.now(timezone.utc).isoformat(),
                "indexed_at": datetime.now(timezone.utc).isoformat(),
                "days_running": _calc_days_running(ad["first_seen"]),
            }
            await es.index(index="ads", id=ad["ad_id"], document=doc)
        await es.indices.refresh(index="ads")
        count = await es.count(index="ads")
        print(f"Seeded {len(SAMPLE_ADS)} ads. Index now has {count['count']} docs.")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
