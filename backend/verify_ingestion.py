"""
Verify the best-performing scorer + e-commerce filter on realistic ad data.

This exercises every decision branch the scraper pipeline will hit in production
(full body copy with prices/CTAs, scaling via duplicate variants, and the four
spam categories we filter out). Run:

    venv/Scripts/python.exe verify_ingestion.py
"""

from datetime import datetime, timezone

from app.ingestion.scraper import RawAd
from app.ingestion.scoring import score_ad
from app.ingestion.pipeline import _assign_variant_counts

NOW = int(datetime.now(timezone.utc).timestamp())


def days_ago(n: int) -> int:
    return NOW - n * 86400


def ad(ad_id, page_id, name, body, days, country="TN"):
    return RawAd(
        ad_id=ad_id, page_id=page_id, page_name=name, body_text=body,
        start_ts=days_ago(days), is_active=True, country=country,
    )


# (RawAd, expected_keep, label)
CASES = [
    # ── e-commerce winners (long-running) → KEEP ──────────────────────
    (ad("1", "p1", "AVA.tn",
        "9 styles au choix - Livraison gratuite partout en Tunisie. Commandez maintenant à 89 DT seulement!",
        40), True, "FR e-com, 40d running"),
    (ad("2", "p2", "Animalerie.saad",
        "💰 180 DH seulement 🚚 Livraison gratuite. Commandez maintenant", 20, "MA"),
     True, "FR/price e-com, 20d"),
    (ad("3", "p3", "Glow Cosmetics",
        "خصم 50% على كريم التفتيح. اطلبي الآن والتوصيل مجاني. السعر 120 ر.س", 15, "SA"),
     True, "AR e-com w/ price, 15d"),

    # ── e-commerce + scaling (fresh but many variants) → KEEP ─────────
    (ad("4a", "p4", "Styles Lunette", "Lunettes de soleil polarisées UV400 - Livraison Gratuite", 3, "MA"), True, "scaling variant"),
    (ad("4b", "p4", "Styles Lunette", "Lunettes de soleil polarisées UV400 - Livraison Gratuite", 3, "MA"), True, "scaling variant"),
    (ad("4c", "p4", "Styles Lunette", "Lunettes de soleil polarisées UV400 - Livraison Gratuite", 2, "MA"), True, "scaling variant"),
    (ad("4d", "p4", "Styles Lunette", "Lunettes de soleil polarisées UV400 - Livraison Gratuite", 1, "MA"), True, "scaling variant"),

    # ── spam: game / ebook / drama / app → DROP even if long+scaled ───
    (ad("5", "p5", "Lanter Odyssey",
        "🚀 2025's #1 mobile game is live! Complete quests and boss battles to earn diamonds. Install now",
        300), False, "GAME spam (long+scaled, still dropped)"),
    (ad("6", "p6", "Romantic Lover",
        "Read Now 👉 The Alpha's rejected mate — continue reading chapter 1", 168, "AE"),
     False, "EBOOK spam"),
    (ad("7", "p7", "دراما ممتازة", "#Goodshort مسلسلات قصيرة رائعة", 90, "SA"), False, "DRAMA spam"),
    (ad("8", "p8", "Fantasy Reading", "🔞Attention! Do not read in public 👉", 60, "AE"), False, "APP spam"),

    # ── e-commerce but unproven (fresh, single) → DROP low-perf ───────
    (ad("9", "p9", "New Shop", "Livraison gratuite, commandez à 50 DT", 2), False, "fresh single e-com (low-perf)"),
]


def main():
    ads = [c[0] for c in CASES]
    _assign_variant_counts(ads)  # scaling signal needs the whole set

    print(f"{'advertiser':<18}{'days':>5}{'var':>4}{'ecom':>5}{'spam':>7}{'score':>7}  decision")
    print("-" * 70)
    passed = 0
    for raw, expected_keep, label in CASES:
        s = score_ad(raw, NOW)
        ok = s.keep == expected_keep
        passed += ok
        mark = "✅" if ok else "❌"
        decision = "KEEP" if s.keep else f"drop({s.spam_reason or 'low-perf'})"
        print(f"{raw.page_name[:17]:<18}{s.days_running:>5}{s.variant_count:>4}"
              f"{s.ecom_signals:>5}{(s.spam_reason or '-'):>7}{s.score:>7}  {mark} {decision}")

    print("-" * 70)
    print(f"{passed}/{len(CASES)} cases matched expectations.")
    if passed != len(CASES):
        raise SystemExit("Some cases did not match expected keep/drop decisions.")


if __name__ == "__main__":
    main()
