"""
Product Dossier — "the complete business in a box" for one winning ad.

One click on a winner answers the only question a seller actually has:
"what is this product, and will it make ME money?"

  • identity + economics (LLM, ~1 call): what the product is, who buys it,
    realistic AliExpress supply-cost band, angles worth stealing.
  • margin math (server-side, honest): extracted sell price from the ad copy
    − supply cost − typical MENA COD/shipping fees → margin %.
  • saturation + market-gap map (pure ES, free to serve): how many brands run
    this product, in which markets — and which swept markets are still OPEN.
    This is the sentence nobody else can produce for MENA.

Costs 2 credits (the route enforces it); the ES parts cost us nothing.
"""

import json
import logging
import re
from urllib.parse import quote_plus

from app.ai.script_generator import _call_llm
from app.core.elasticsearch import get_es_client, find_similar_product_ads
from app.ingestion.pipeline import DEFAULT_COUNTRIES, GLOBAL_COUNTRIES

logger = logging.getLogger("adspy.dossier")

# Rough USD conversion for prices found in ad copy (marketing math, not forex).
_CURRENCY_USD = {
    "tnd": 0.32, "dt": 0.32, "د.ت": 0.32,
    "mad": 0.10, "dh": 0.10,
    "dzd": 0.0074, "دج": 0.0074,
    "egp": 0.020, "ج.م": 0.020,
    "sar": 0.27, "ر.س": 0.27,
    "aed": 0.27, "د.إ": 0.27,
    "kwd": 3.25, "qar": 0.27,
    "eur": 1.08, "€": 1.08,
    "usd": 1.0, "$": 1.0,
}
_PRICE_FIND_RE = re.compile(
    r"(\d[\d.,]*)\s?(tnd|dt|mad|dh|dzd|egp|sar|aed|kwd|qar|eur|usd|€|\$|ر\.?س|ج\.?م|د\.?إ|دج|د\.?ت)"
    r"|(€|\$)\s?(\d[\d.,]*)",
    re.IGNORECASE,
)
# What COD + local shipping + returns typically eat in MENA e-com.
_FEES_PCT = 0.18


_SHIPPING_WORDS = ("livraison", "توصيل", "شحن", "delivery", "shipping", "فقط للتوصيل")


def extract_price(text: str) -> tuple[float, str] | None:
    """The product's SELL price from ad copy; None when there isn't one.

    MENA ad boilerplate is full of decoy numbers: "Livraison 7 DT" (delivery
    fee) and crossed-out old prices ("100 DT → 49 DT"). So: drop any price
    whose surrounding text mentions shipping, then take the LOWEST remaining —
    in promo copy the lowest non-shipping price is the actual offer.
    """
    text = text or ""
    candidates: list[tuple[float, str]] = []
    for m in _PRICE_FIND_RE.finditer(text):
        raw, cur = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        cleaned = raw.replace(",", ".").rstrip(".")
        # "1.299" style thousands → 1299
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")
        try:
            amount = float(cleaned)
        except ValueError:
            continue
        if not (0.5 <= amount <= 100000):
            continue
        # Fee patterns put the word BEFORE the number ("livraison 7dt",
        # "التوصيل 10"); looking only backwards keeps "49 DT livraison
        # gratuite" (free shipping AFTER the price) as a valid sell price.
        ctx = text[max(0, m.start() - 20): m.start()].lower()
        if any(w in ctx for w in _SHIPPING_WORDS):
            continue
        candidates.append((amount, cur.lower().replace(" ", "")))
    if not candidates:
        return None
    return min(candidates, key=lambda c: c[0])


def _to_usd(amount: float, currency: str) -> float | None:
    rate = _CURRENCY_USD.get(currency.replace(".", ""))
    return round(amount * rate, 2) if rate else None


def saturation(brand_count: int) -> tuple[str, str]:
    """(level, plain-words meaning) from how many brands run this product.

    Wording is grounded in what we actually observe — OUR winners catalog
    (the top ~120 ads per market), not the whole Ad Library. Absence here
    means "no proven winner detected", never "nobody runs it" — that claim
    burned us once and the verify-live links exist for exactly this reason.
    """
    if brand_count <= 1:
        return "wide_open", "No other winner detected in our catalog — verify live, then move fast."
    if brand_count <= 4:
        return "heating_up", "A few proven winners are on it — validated, still room to win."
    if brand_count <= 9:
        return "crowded", "Plenty of proven competition — you'll need a stronger angle or a fresh market."
    return "saturated", "Winners everywhere — only enter with a real edge (or pick the gap markets)."


# Which language a buyer-facing Ad Library search should use, per market.
_FR_MARKETS = {"TN", "MA", "DZ", "FR"}
_AR_MARKETS = {"EG", "SA", "AE", "KW", "QA"}


def _adlib_verify_url(country: str, llm: dict, fallback: str) -> str:
    """Public Facebook Ad Library search for this product in one market —
    the one-click 'is our catalog missing something?' truth check."""
    if country in _FR_MARKETS:
        term = llm.get("product_keywords_fr") or fallback
    elif country in _AR_MARKETS:
        term = llm.get("product_keywords_ar") or llm.get("product_keywords_fr") or fallback
    else:
        term = llm.get("sourcing_search_term") or fallback
    return ("https://www.facebook.com/ads/library/?active_status=active&ad_type=all"
            f"&country={country}&q={quote_plus(term)}&search_type=keyword_unordered&media_type=all")


_SYSTEM = """You are a senior e-commerce product analyst for MENA dropshippers.
Given a winning ad, identify the product and its economics. Be honest and specific.
Reply with STRICT JSON only, exactly this shape:
{
 "product_name": "short product name",
 "category": "niche/category",
 "what_it_is": "1-2 sentences: what the product is and the problem it solves",
 "target_audience": "who buys it, 1 sentence",
 "est_supply_cost_usd_min": 2.5,
 "est_supply_cost_usd_max": 6.0,
 "sourcing_search_term": "3-6 word english term to find it on AliExpress",
 "sourcing_search_term_fr": "3-6 word FRENCH term for Tunisian directories and Google (e.g. 'complément alimentaire minceur gélules')",
 "product_keywords_fr": "2-4 word FRENCH product term as a buyer would say it (e.g. 'traitement mycose ongles')",
 "product_keywords_ar": "2-4 word ARABIC product term (e.g. 'علاج فطريات الأظافر')",
 "is_supplement": false,
 "is_cosmetic": false,
 "tunisia_manufacturable": false,
 "tunisia_manufacturing_note": "1 sentence: what kind of Tunisian maker could produce it (or empty string)",
 "winning_angles": ["angle 1", "angle 2", "angle 3"],
 "risk_notes": "1-2 sentences: seasonality, shipping fragility, saturation, ad-policy risks",
 "verdict_line": "one punchy sentence: should a seller move on this now, and how"
}
Supply cost = realistic AliExpress/1688 unit price band for this kind of product.
is_supplement = true for food supplements, vitamins, slimming/hair/skin ingestibles.
is_cosmetic = true for topical beauty/care products (creams, serums, oils, soaps).
tunisia_manufacturable = true when Tunisian industry realistically produces this
category (supplements/parapharma via contract labs, textiles & clothing, leather,
olive-oil cosmetics, packaged food, furniture/wood, simple plastic goods) —
false for consumer electronics, complex gadgets, and molded technical products.
No markdown, no commentary — JSON only."""

# 🇹🇳 Local sourcing — the edge China can't match: no customs, 1-week restock,
# COD-friendly cash cycles, and "made in Tunisia" as a marketing angle.
# VERIFIED Tunisian façonniers (real companies, direct sites — researched
# 2026-07-04). MOQ/certifications still the user's job to confirm.
_TN_SUPPLEMENT_LABS = [
    {"name": "Medicka Lab", "url": "https://medickalab.com/",
     "note": "Façonnier leader de compléments alimentaires (depuis 2010, Nabeul) — FSSC 22000, gélules/comprimés, marque blanche A→Z"},
    {"name": "Galevit Laboratoires", "url": "https://www.galevit.tn/",
     "note": "Phytothérapie & compléments alimentaires fabriqués en Tunisie"},
    {"name": "Vibraforce", "url": "https://vibraforce.com/",
     "note": "Façonnier compléments bio — marque blanche, petites quantités (idéal pour tester)"},
]
_TN_COSMETIC_LABS = [
    {"name": "Heisenberg Lab", "url": "https://www.heisenberglab.com/",
     "note": "Laboratoire de fabrication cosmétique en Tunisie — façonnage & marque blanche"},
    {"name": "Vibraforce", "url": "https://vibraforce.com/",
     "note": "Façonnage de cosmétiques bio/naturels — marque blanche, petites quantités"},
]


def _google(q: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(q)}"


def _tn_sources(term_fr: str, is_supplement: bool, is_cosmetic: bool) -> list[dict]:
    """Tunisian manufacturer leads: verified labs per category + B2B
    directories for everything. `term_fr` MUST be French — Tunisian
    directories and Google give nothing useful for English queries."""
    sources: list[dict] = []
    if is_supplement:
        sources += _TN_SUPPLEMENT_LABS
        sources.append({
            "name": "Autres façonniers 🇹🇳", "note": "Recherche Google — fabricants de compléments en Tunisie",
            "url": _google(f"façonnage complément alimentaire Tunisie fabricant {term_fr}"),
        })
    if is_cosmetic:
        sources += [lab for lab in _TN_COSMETIC_LABS if lab["name"] not in {s["name"] for s in sources}]
        sources.append({
            "name": "Autres labos cosmétiques 🇹🇳", "note": "Recherche Google — façonniers cosmétiques en Tunisie",
            "url": _google(f"façonnage cosmétique Tunisie laboratoire marque blanche {term_fr}"),
        })
    sources += [
        {"name": "Kompass Tunisie", "note": "Annuaire B2B des fabricants tunisiens",
         "url": f"https://tn.kompass.com/searchCompanies?text={quote_plus(term_fr)}"},
        {"name": "Europages Tunisie", "note": "Fournisseurs & exportateurs tunisiens par produit",
         "url": f"https://www.europages.fr/entreprises/Tunisie/{quote_plus(term_fr)}.html"},
        {"name": "Tunisie Industrie (APII)", "note": "Base officielle de l'industrie — recherche par activité",
         "url": "http://www.tunisieindustrie.nat.tn/fr/dbi.asp"},
    ]
    return sources


async def generate_dossier(ad_id: str, ad: dict) -> dict:
    """Assemble the full dossier for one indexed ad (LLM + ES + math).

    The LLM runs FIRST: its per-language product keywords make the similarity
    query cross-language (an AR-copy seller of the same product in TN must
    count as competition for this FR-copy ad).
    """
    price = extract_price(ad.get("copy_text", ""))
    price_local = {"amount": price[0], "currency": price[1].upper()} if price else None
    price_usd = _to_usd(*price) if price else None

    # LLM: product identity + supply economics + per-language keywords.
    price_line = (
        f"{price_local['amount']} {price_local['currency']} (~${price_usd} USD)"
        if price_usd and price_local else "not stated"
    )
    user_prompt = (
        f"AD COPY:\n{(ad.get('copy_text') or '')[:2000]}\n\n"
        f"CTA: {ad.get('cta_text') or '-'}\n"
        f"LANDING PAGE: {ad.get('landing_page') or '-'}\n"
        f"ADVERTISER: {ad.get('advertiser_name')}\n"
        f"SELL PRICE FOUND IN AD: {price_line}\n"
        "Return the JSON."
    )
    llm: dict = {}
    for _attempt in range(2):  # one retry — a flaky LLM reply must not 502 a paid feature
        raw = await _call_llm(_SYSTEM, user_prompt)
        try:
            llm = json.loads(raw)
        except (ValueError, TypeError):
            m = re.search(r"\{.*\}", raw or "", re.DOTALL)
            try:
                llm = json.loads(m.group()) if m else {}
            except (ValueError, TypeError):
                llm = {}
        if llm.get("product_name"):
            break

    keywords = {
        "fr": llm.get("product_keywords_fr"),
        "ar": llm.get("product_keywords_ar"),
        "en": llm.get("sourcing_search_term"),
    }
    es = get_es_client()
    try:
        similar = await find_similar_product_ads(es, ad_id, keywords=keywords)
    except Exception as e:  # noqa: BLE001 — similarity is additive, not fatal
        logger.warning("similar-product query failed for %s: %s", ad_id, e)
        similar = {"similar_ads": 0, "brand_count": 1, "market_presence": {}, "top_brands": []}
    finally:
        await es.close()

    # Market-gap map over everything we sweep. Presence counts include the ad
    # itself. "Open" strictly means "no winner in OUR catalog" — each open
    # market ships a live Ad Library link so the user can verify in one click.
    presence = dict(similar["market_presence"])
    for c in ad.get("countries") or [ad.get("country")]:
        if c:
            presence[c] = max(presence.get(c, 0), 1)
    open_mena = [c for c in DEFAULT_COUNTRIES if not presence.get(c)]
    open_global = [c for c in GLOBAL_COUNTRIES if not presence.get(c)]
    brand_count = max(similar["brand_count"], 1)
    sat_level, sat_meaning = saturation(brand_count)
    fallback_term = llm.get("product_name") or ad.get("advertiser_name") or ""
    verify_urls = {
        c: _adlib_verify_url(c, llm, fallback_term)
        for c in [*open_mena, *open_global, *presence]
    }

    # Server-side margin math — honest, and never trusts LLM arithmetic.
    margin = None
    pricing_hint = None
    supply_min = llm.get("est_supply_cost_usd_min")
    supply_max = llm.get("est_supply_cost_usd_max")
    if isinstance(supply_min, (int, float)) and isinstance(supply_max, (int, float)):
        supply_mid = (supply_min + supply_max) / 2
        if price_usd:
            fees = round(price_usd * _FEES_PCT, 2)
            profit = round(price_usd - supply_mid - fees, 2)
            margin = {
                "sell_price_usd": price_usd,
                "supply_cost_usd_min": supply_min,
                "supply_cost_usd_max": supply_max,
                "est_fees_usd": fees,          # COD + shipping + returns (~18%)
                "est_profit_usd": profit,
                "margin_pct": round(profit / price_usd * 100, 1),
            }
        else:
            # No price in the ad — give the typical COD playbook (3–4× supply)
            # so the seller still leaves with numbers, clearly labeled as a hint.
            pricing_hint = {
                "supply_cost_usd_min": supply_min,
                "supply_cost_usd_max": supply_max,
                "suggested_sell_usd_min": round(supply_mid * 3, 2),
                "suggested_sell_usd_max": round(supply_mid * 4, 2),
            }

    term = llm.get("sourcing_search_term") or llm.get("product_name") or ""
    # Tunisia-facing searches in FRENCH (fall back to the product name, which
    # for MENA ads is usually already FR/AR) — never the English China term.
    term_fr = llm.get("sourcing_search_term_fr") or llm.get("product_name") or term
    is_supplement = bool(llm.get("is_supplement"))
    is_cosmetic = bool(llm.get("is_cosmetic"))
    # Supplements & cosmetics are always locally manufacturable (façonniers exist).
    tn_feasible = is_supplement or is_cosmetic or bool(llm.get("tunisia_manufacturable"))
    sourcing = {
        "search_term": term,
        "aliexpress_url": f"https://www.aliexpress.com/w/wholesale-{quote_plus(term)}.html" if term else None,
        "alibaba_url": f"https://www.alibaba.com/trade/search?SearchText={quote_plus(term)}" if term else None,
        "made_in_china_url": (
            f"https://www.made-in-china.com/products-search/hot-china-products/{quote_plus(term)}.html"
            if term else None
        ),
        "local": {
            "feasible": tn_feasible,
            "is_supplement": is_supplement,
            "note": (llm.get("tunisia_manufacturing_note") or "").strip()
                    or ("Supplements can be produced by Tunisian contract labs (façonnage) — "
                        "local stock, no customs, and a 🇹🇳 'made in Tunisia' trust angle."
                        if is_supplement else ""),
            "tunisia_sources": _tn_sources(term_fr, is_supplement, is_cosmetic) if tn_feasible else [],
        },
    }

    return {
        "ad_id": ad_id,
        "product": {
            "name": llm.get("product_name") or ad.get("advertiser_name"),
            "category": llm.get("category"),
            "what_it_is": llm.get("what_it_is"),
            "target_audience": llm.get("target_audience"),
        },
        "proof": {
            "heat": ad.get("heat"),
            "momentum": ad.get("momentum"),
            "variant_count": ad.get("variant_count"),
            "days_running": ad.get("days_running"),
            "est_spend_min_usd": ad.get("est_spend_min_usd"),
            "est_spend_max_usd": ad.get("est_spend_max_usd"),
            "brand_live_ads": ad.get("brand_live_ads"),
        },
        "price_local": price_local,
        "margin": margin,
        "pricing_hint": pricing_hint,
        "market_map": {
            "presence": presence,           # {country: similar-ad count in OUR catalog}
            "open_mena": open_mena,         # swept MENA markets with no winner IN OUR CATALOG
            "open_global": open_global,
            "saturation": sat_level,
            "saturation_meaning": sat_meaning,
            "brand_count": brand_count,
            "verify_urls": verify_urls,     # one-click live Ad Library check per market
        },
        "competitors": similar["top_brands"],
        "angles": llm.get("winning_angles") or [],
        "risk_notes": llm.get("risk_notes"),
        "verdict_line": llm.get("verdict_line"),
        "sourcing": sourcing,
        # Per-language product terms — the UI's "spy similar winners" deep link.
        "keywords": {k: v for k, v in keywords.items() if v},
    }
