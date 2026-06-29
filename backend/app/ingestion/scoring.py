"""
Best-performing ad scoring + e-commerce filtering.

We keep an ad only if it looks like a *winner* worth spying on:

  1. Long-running   — still active after N+ days. Advertisers kill losers fast,
                      so longevity is the strongest free proxy for profitability.
  2. Scaling        — the same advertiser runs many copies/variants of one
                      creative. Duplication = they found a winner and are
                      pouring budget into it.
  3. E-commerce     — it's a genuine product/store ad, not the spam that floods
                      the Ad Library (mobile games, ebook/novel clickbait, short
                      drama apps, generic "free app" installs).

Thresholds are tunable via settings (INGEST_MIN_DAYS_RUNNING, etc.).
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.ingestion.scraper import RawAd


# ─── Spam categories (NOT e-commerce) ──────────────────────────────────────
_GAME_RE = re.compile(
    r"\b(mobile game|rpg|boss battle|quest[s]?|diamonds|gems|install now|play now|"
    r"level up|summon|gacha|raid|guild|idle game|#1 (mobile )?game|epic loot)\b",
    re.IGNORECASE,
)
_EBOOK_RE = re.compile(
    r"(read now|continue reading|continuer la lecture|chapter \d|the alpha|"
    r"werewolf|billionaire|luna|my ex[- ]?(husband|wife)|the ceo|mr\.\s|"
    r"divorce|rejected mate|fated to)",
    re.IGNORECASE,
)
_DRAMA_RE = re.compile(
    r"(#?goodshort|short drama|shortmax|dramabox|reelshort|micro[- ]?drama|"
    r"مسلسل|مسلسلات|دراما|أفلام قصيرة|فيلم قصير|مسرح)",
    re.IGNORECASE,
)
_APP_RE = re.compile(
    r"(free app|download the app|تطبيق مجاني|do not read in public|attention!)",
    re.IGNORECASE,
)

# Global marketplaces / mega-advertisers — technically "winners" but useless as
# product/creative inspiration for a local dropshipper. Filtered out so the
# results stay focused on inspirable product winners. Extend via INGEST_EXCLUDE_BRANDS.
_GLOBAL_MARKETPLACES = {
    "alibaba", "aliexpress", "temu", "shein", "wish.com", "amazon", "ebay",
    "banggood", "dhgate", "lazada", "joom", "zaful", "romwe", "masterclass",
    "booking.com", "agoda", "aliexpress.com",
}


def _is_global_marketplace(name: str) -> bool:
    n = (name or "").lower()
    extra = [b.strip().lower() for b in str(getattr(settings, "INGEST_EXCLUDE_BRANDS", "") or "").split(",") if b.strip()]
    return any(b in n for b in _GLOBAL_MARKETPLACES) or any(b and b in n for b in extra)

# ─── E-commerce positive signals ───────────────────────────────────────────
# Latin keywords use word boundaries.
_ECOM_LATIN_RE = re.compile(
    r"\b(livraison|gratuite?|commander|commande|achetez|achat|prix|promo|soldes|"
    r"offre|stock|r[ée]duction|pr[ée]commande|shop\s?now|order\s?now|buy\s?now|"
    r"order|shop|sale|discount|free\s?delivery|cod|cash\s?on\s?delivery)\b",
    re.IGNORECASE,
)
# Arabic terms are matched as SUBSTRINGS — Arabic glues prefixes (الـ/وـ/بـ/لـ/فـ)
# onto words, so \b word boundaries never match (e.g. التوصيل contains توصيل).
_ECOM_AR = [
    "اطلب", "اطلبي", "طلب", "كومند", "توصيل", "تسوق", "تسوقي", "خصم", "تخفيض",
    "عرض", "السعر", "سعر", "ثمن", "الكمية", "متوفر", "شحن", "اشتري", "اشتر",
    "للبيع", "دينار", "درهم", "ريال", "جنيه", "اونلاين", "اطلبه",
]
# Storefront / DTC signals in the landing URL.
_SHOP_URL_RE = re.compile(
    r"(converty|shopify|youcan|woocommerce|wetroc|/product|/products|order|shop|store|boutique|cart|checkout)",
    re.IGNORECASE,
)
# CTA buttons that signal a transaction.
_ECOM_CTA_RE = re.compile(
    r"(order|shop|buy|book|get\s?offer|sign\s?up|اطلب|تسوق|احجز|اشتر|اشتري)", re.IGNORECASE
)
# Price patterns: "180 DH", "25 DT", "99 TND", "ر.س 50", "$19.99", "€29", "30 ج.م"
_PRICE_RE = re.compile(
    r"(\d[\d.,]*\s?(dh|dt|tnd|mad|dzd|sar|egp|aed|kwd|qar|eur|usd|€|\$|ر\.?س|ج\.?م|د\.?إ|دج|د\.?ت)"
    r"|(dh|dt|tnd|mad|dzd|sar|egp|aed|€|\$|ر\.?س|ج\.?م)\s?\d)",
    re.IGNORECASE,
)


@dataclass
class AdScore:
    days_running: int
    variant_count: int
    ecom_signals: int
    is_ecommerce: bool
    strong_commerce: bool     # storefront URL / price / multiple hard signals
    spam_reason: str          # "" when not spam
    score: float              # 0..100 "printed money" proxy
    keep: bool


def _days_running(start_ts: Optional[int], end_ts: Optional[int], now_ts: int) -> int:
    if not start_ts:
        return 0
    end = end_ts if end_ts else now_ts
    return max(0, int((end - start_ts) // 86400))


def _classify_ecommerce(text: str, link_url: str = "", cta: str = "") -> tuple[bool, int, bool, str]:
    """Return (is_ecommerce, ecom_signal_count, strong_commerce, spam_reason).

    Scans the creative text (Arabic as substrings), the CTA button, and the
    landing URL — all strong commerce signals in Ad Library data.

    `strong_commerce` flags a *hard* transactional signal — a real storefront
    URL, a visible price, or several commerce cues together — as opposed to a
    single stray keyword (e.g. the word "offre" in a brand-awareness post). It's
    what separates a product that actually sells from a long-running brand/app
    ad that merely mentions a shoppy word.
    """
    signals = len(_ECOM_LATIN_RE.findall(text))
    signals += sum(1 for w in _ECOM_AR if w in text)
    has_price = bool(_PRICE_RE.search(text))
    if has_price:
        signals += 1
    has_cta = bool(cta and _ECOM_CTA_RE.search(cta))
    if has_cta:
        signals += 1
    has_shop_url = bool(link_url and _SHOP_URL_RE.search(link_url))
    if has_shop_url:
        signals += 1

    # Strong-spam categories: drop unless the ad ALSO shows real commerce intent.
    for label, rx in (("game", _GAME_RE), ("ebook", _EBOOK_RE), ("drama", _DRAMA_RE), ("app", _APP_RE)):
        if rx.search(text) and signals < 2:
            return False, signals, False, label

    # A genuine seller: storefront link, a price, or a transactional CTA backed
    # by at least one more cue, or a pile of commerce keywords.
    strong = has_shop_url or has_price or (has_cta and signals >= 2) or signals >= 3
    return signals >= 1, signals, strong, ""


def score_ad(ad: RawAd, now_ts: Optional[int] = None) -> AdScore:
    now_ts = now_ts or int(datetime.now(timezone.utc).timestamp())
    text = ad.primary_text

    days = _days_running(ad.start_ts, ad.end_ts, now_ts)
    variants = max(1, ad.variant_count)
    is_ecom, ecom_signals, strong_commerce, spam_reason = _classify_ecommerce(text, ad.link_url, ad.cta_text)
    if not spam_reason and _is_global_marketplace(ad.page_name):
        spam_reason = "marketplace"  # global mega-brand, not inspirable

    min_days = int(getattr(settings, "INGEST_MIN_DAYS_RUNNING", 7))
    min_variants = int(getattr(settings, "INGEST_MIN_VARIANTS", 3))

    # "Printed money" 0..100 proxy. We can't see spend, so we infer it:
    #   • SCALING (variant_count) is the strongest free signal — advertisers only
    #     duplicate a creative they're profiting from, so it leads at 45%.
    #   • LONGEVITY supports it (30%) — kept alive = still converting — but alone
    #     it's noisy (brand/app ads run long too), so it no longer dominates.
    #   • COMMERCE strength (25%) confirms it's a product that actually sells.
    # Confirmed sellers (real storefront / price) get a small boost.
    days_c = min(days, 180) / 180
    scale_c = min(variants, 25) / 25
    ecom_c = min(ecom_signals, 5) / 5
    base = 100 * (0.30 * days_c + 0.45 * scale_c + 0.25 * ecom_c)
    if strong_commerce:
        base *= 1.10
    score = round(min(100.0, base), 1)

    # Keep a winner only if it's genuinely e-commerce AND shows it's printing
    # money: either real scaling, OR longevity backed by a hard commerce signal.
    # The longevity branch now REQUIRES strong_commerce, which is what stops
    # long-running non-ecom (brand/app) ads from leaking in on days alone.
    scaling_winner = variants >= min_variants
    longevity_winner = days >= min_days and strong_commerce
    keep = not spam_reason and is_ecom and (scaling_winner or longevity_winner)

    return AdScore(
        days_running=days,
        variant_count=variants,
        ecom_signals=ecom_signals,
        is_ecommerce=is_ecom,
        strong_commerce=strong_commerce,
        spam_reason=spam_reason,
        score=score,
        keep=keep,
    )
