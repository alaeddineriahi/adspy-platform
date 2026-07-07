"""
Ingestion pipeline: scrape -> score -> filter -> dedup -> upsert.

This is the self-serve engine. It sweeps a set of MENA countries and seed search
terms, keeps only the best-performing e-commerce ads (see scoring.py), and
upserts them into the Elasticsearch `ads` index. Called both by the scheduler
(autonomous) and by the manual trigger endpoint.
"""

import asyncio
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.elasticsearch import get_es_client, setup_index
from app.models.brand import BrandSnapshot
from app.ingestion.scraper import RawAd, fetch_ads, fetch_page_ads
from app.ingestion.radar import (
    detect_ad_events,
    brand_escalation_event,
    brand_expansion_event,
    record_events,
)
from app.ingestion.scoring import score_ad, compute_heat
from app.ingestion.spend import estimate_spend
from app.ingestion.eu_reach import EU_COUNTRIES, fetch_eu_reach, apply_reach_to_doc
from app.ingestion.media import mirror_to_r2, r2_enabled

logger = logging.getLogger("adspy.ingest")

# Core markets — the user's region.
DEFAULT_COUNTRIES = ["TN", "MA", "DZ", "EG", "SA", "AE", "KW", "QA"]
# Trend markets — where e-com trends originate; what scales there reaches MENA
# months later. Swept together with the core (ONE sweep covers everything);
# they only differ by a lower per-country cap (INGEST_GLOBAL_MAX_PER_COUNTRY).
GLOBAL_COUNTRIES = ["US", "CA", "GB", "AU", "FR"]


def _global_set() -> set[str]:
    return set(_as_list(getattr(settings, "INGEST_GLOBAL_COUNTRIES", None), GLOBAL_COUNTRIES))


def sweep_countries() -> list[str]:
    """The full default sweep scope: core markets + global trend markets.

    One list, one sweep, one schedule — a rebuilt feed or a scheduled run always
    covers every market the product sells. Global markets can still be switched
    off wholesale via INGEST_GLOBAL_ENABLED.
    """
    core = _as_list(getattr(settings, "INGEST_COUNTRIES", None), DEFAULT_COUNTRIES)
    if not bool(getattr(settings, "INGEST_GLOBAL_ENABLED", True)):
        return core
    glob = _as_list(getattr(settings, "INGEST_GLOBAL_COUNTRIES", None), GLOBAL_COUNTRIES)
    return core + [c for c in glob if c not in core]


def cap_for(country: str, core_cap: int) -> int:
    """Per-market keep cap: trend markets get a lower one (coverage over depth —
    what matters there is spotting the trend, not exhausting the market)."""
    if country in _global_set():
        return min(core_cap, int(getattr(settings, "INGEST_GLOBAL_MAX_PER_COUNTRY", 60)))
    return core_cap

# Discovery is about finding WINNING PRODUCTS, not matching discount words — and
# not the app/game/marketplace noise that a blank "browse everything" pulls in.
# So we sweep broad PRODUCT CATEGORIES across niches; searching a category
# structurally excludes games/apps, and the winner-scoring (longevity + scaling
# + e-commerce, global marketplaces filtered) surfaces the winners.
# Want the raw firehose? Pass "" as a search term in the UI. Want a niche? Type it.
# The vocabulary spans the 15 highest-margin / most-scalable e-com niches
# (health & supplements, beauty, personal care, fashion, pets, home & kitchen,
# fitness, electronics/gadgets, baby, jewelry, sleep, automotive, food & bev,
# mental wellness, gaming). A beauty-heavy list is why discovery came back all
# fragrance/skincare; covering every niche is what makes it wide.
#
# It's big on purpose, so a single sweep does NOT query all of it (that would
# hammer the FB session). `default_terms_for` returns a ROTATING slice — each
# sweep covers a different window, so the whole vocabulary cycles through over
# a day or two while per-run query volume stays bounded.
EN_NICHE_TERMS = [
    "supplement", "collagen", "probiotic", "greens powder",          # health & supplements
    "serum", "skincare", "retinol", "perfume",                       # beauty & skincare
    "teeth whitening", "hair growth", "electric toothbrush",         # personal care
    "sneakers", "leggings", "shapewear", "sunglasses", "watch",      # fashion & apparel
    "dog", "pet", "cat",                                             # pets
    "kitchen gadget", "home organizer", "cleaning",                  # home & kitchen
    "resistance bands", "massage gun", "fitness",                    # fitness & sports
    "earbuds", "phone accessory", "led lights",                      # electronics & gadgets
    "baby", "toddler",                                              # baby & kids
    "jewelry", "necklace", "bracelet",                              # jewelry & accessories
    "pillow", "sleep",                                             # sleep products
    "car accessory",                                              # automotive
    "coffee", "snack",                                            # food & beverage
    "anxiety relief", "stress relief",                             # mental wellness
    "gaming headset", "controller",                               # gaming accessories
]
FR_NICHE_TERMS = [
    "complément alimentaire", "collagène", "probiotique",            # santé & compléments
    "sérum", "cosmétique", "crème", "parfum",                        # beauté
    "blanchiment dents", "cheveux", "brosse à dents électrique",     # soin personnel
    "chaussures", "legging", "gaine amincissante", "lunettes", "montre",  # mode
    "chien", "chat", "animaux",                                     # animaux
    "cuisine", "rangement", "nettoyage",                            # maison
    "fitness", "musculation", "yoga",                              # sport
    "écouteurs", "gadget", "led",                                  # électronique
    "bébé", "enfant",                                             # bébé & enfants
    "bijoux", "collier", "bracelet",                               # bijoux
    "oreiller", "sommeil",                                        # sommeil
    "accessoire voiture",                                        # auto
    "café", "minceur",                                           # alimentation / santé
    "anti-stress",                                              # bien-être mental
    "manette gaming",                                           # gaming
]
AR_NICHE_TERMS = [
    "مكملات غذائية", "كولاجين",                # supplements
    "سيروم", "عطر", "كريم", "عناية بالبشرة",   # beauty
    "تبييض الاسنان", "الشعر",                  # personal care
    "حذاء", "نظارات", "ساعة", "حزام تنحيف",     # fashion
    "كلاب", "قطط", "حيوانات اليفة",            # pets
    "مطبخ", "تنظيف", "تنظيم المنزل",           # home & kitchen
    "لياقة", "رياضة",                          # fitness
    "سماعات", "اضاءة",                         # electronics
    "اطفال", "بيبي",                           # baby
    "مجوهرات", "قلادة", "اسورة",                # jewelry
    "وسادة", "نوم",                            # sleep
    "اكسسوارات السيارة",                       # automotive
    "قهوة", "تخسيس",                           # food / health
    "العاب",                                   # gaming
]
# MENA core markets are FR+AR — sweep both vocabularies there.
DEFAULT_SEARCH_TERMS = FR_NICHE_TERMS + AR_NICHE_TERMS

_EN_MARKETS = {"US", "CA", "GB", "AU"}


def _rotating_slice(terms: list[str], n: int) -> list[str]:
    """A window of `n` terms that advances every sweep, cycling the full vocab.

    Keeps per-sweep FB query volume bounded while covering every niche across
    consecutive runs (window keyed to the sweep interval)."""
    if n <= 0 or len(terms) <= n:
        return terms
    interval_h = float(getattr(settings, "INGEST_INTERVAL_HOURS", 12)) or 12
    window = int(datetime.now(timezone.utc).timestamp() // (interval_h * 3600))
    off = (window * n) % len(terms)
    return (terms + terms)[off:off + n]


def default_terms_for(country: str) -> list[str]:
    """Per-market niche terms — English for EN markets, no Arabic in France —
    returned as a rotating slice so the full niche vocabulary cycles over time."""
    n = int(getattr(settings, "INGEST_TERMS_PER_SWEEP", 18))
    if country in _EN_MARKETS:
        return _rotating_slice(EN_NICHE_TERMS, n)
    if country == "FR":
        return _rotating_slice(FR_NICHE_TERMS, n)
    env = _as_list(getattr(settings, "INGEST_SEARCH_TERMS", None), [])
    if env:
        return env  # explicit env override — use verbatim, no rotation
    return _rotating_slice(DEFAULT_SEARCH_TERMS, n)

_ARABIC_RE = re.compile(r"[؀-ۿ]")
_FRENCH_RE = re.compile(
    r"[éèàçùêâîôûÉÈÀ]|\b(le|la|les|de|des|du|pour|votre|gratuite|livraison|au|chez|et)\b",
    re.IGNORECASE,
)

# Lightweight run status, surfaced by the /status endpoint.
LAST_RUN: dict = {
    "status": "never_run",
    "started_at": None,
    "finished_at": None,
    "stats": None,
    "alert": None,  # actionable warning (e.g. dead Facebook session) shown in the UI
}


def _as_list(value, default: list[str]) -> list[str]:
    if not value:
        return default
    if isinstance(value, list):
        return value
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _detect_language(text: str, country: str) -> str:
    if _ARABIC_RE.search(text):
        return "ar"
    if _FRENCH_RE.search(text):
        return "fr"
    if country in ("TN", "MA", "DZ") and text.strip() and not text.isascii():
        return "fr"
    return "en"


def _ad_format(ad: RawAd) -> str:
    if ad.videos:
        return "video"
    if len(ad.images) > 1:
        return "carousel"
    return "image"


def creative_key(page_id: str, text: str) -> str:
    """Stable identity for one creative — advertiser + normalized opening copy.

    Near-duplicate collated entries of the same ad share a key, so search can
    collapse them into a single card (with the variant_count badge) instead of
    showing the same creative 3×.
    """
    norm = re.sub(r"[^0-9a-zA-Z؀-ۿ]+", "", (text or "").lower())[:60]
    return f"{page_id}:{norm}"


def _norm_key(ad: RawAd) -> str:
    """Identity used to count how many variants of one creative an advertiser runs."""
    return creative_key(ad.page_id, ad.primary_text)


def _assign_variant_counts(ads: list[RawAd]) -> None:
    groups: dict[str, int] = {}
    for ad in ads:
        groups[_norm_key(ad)] = groups.get(_norm_key(ad), 0) + 1
    for ad in ads:
        # Keep the stronger of Meta's own collation_count and our creative grouping.
        ad.variant_count = max(ad.variant_count, groups[_norm_key(ad)])


def _dedupe_creatives(
    kept: list[tuple[RawAd, "object"]],
) -> list[tuple[RawAd, "object"]]:
    """One indexed doc per creative per market.

    Collated near-duplicates of one creative each arrive as their own ad_id,
    every copy carrying the GROUP's variant_count. Indexing them all burns
    per-market cap slots on copies (search collapses them anyway — a heavily
    collated page once filled a 30-ad deep-dive budget with 30 copies of one
    ad) and multiplies the creative's scaling into every brand aggregate
    (sum(variant_count) counted a 90-variant creative 30×).

    Keep the best-scoring representative — its variant_count already encodes
    the multiplicity. The market stays in the key: the same creative running
    in SA and KW under different ad_ids keeps one doc per market, so
    cross-market presence (gap maps, country filters) survives.
    """
    best: dict[tuple[str, str], tuple[RawAd, object]] = {}
    for ad, s in kept:
        key = (creative_key(ad.page_id, ad.primary_text), ad.country)
        cur = best.get(key)
        if cur is None or s.score > cur[1].score:
            best[key] = (ad, s)
    return list(best.values())


def _to_doc(ad: RawAd, score) -> dict:
    text = ad.primary_text
    now = datetime.now(timezone.utc).isoformat()
    first_seen = (
        datetime.fromtimestamp(ad.start_ts, tz=timezone.utc).isoformat()
        if ad.start_ts else now
    )
    last_seen = (
        datetime.fromtimestamp(ad.end_ts, tz=timezone.utc).isoformat()
        if ad.end_ts else now
    )
    return {
        "ad_id": ad.ad_id,
        "platform": "meta",
        "advertiser_name": ad.page_name,
        "advertiser_id": ad.page_id,
        "country": ad.country,
        "countries": [ad.country],  # grows as other sweeps re-see the same ad
        "language": _detect_language(text, ad.country),
        "ad_format": _ad_format(ad),
        "copy_text": text,
        "cta_text": ad.cta_text,
        "landing_page": ad.link_url or ad.snapshot_url,
        "media_urls": (ad.images + ad.videos),
        "snapshot_url": ad.snapshot_url,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "indexed_at": now,
        "is_active": ad.is_active,
        "days_running": score.days_running,
        "variant_count": score.variant_count,
        "performance_score": score.score,
        "is_ecommerce": score.is_ecommerce,
        "strong_commerce": score.strong_commerce,
        "ecom_signals": score.ecom_signals,
        "creative_key": creative_key(ad.page_id, text),
        "source": "ad_library_scrape",
    }


async def _build_doc(ad: RawAd, s, sem: asyncio.Semaphore) -> dict:
    """Score → doc, with the R2 thumbnail mirror + heat + spend estimate.

    Shared by the keyword sweep and the brand deep-dive so every indexed ad is
    built identically no matter how it was discovered.
    """
    doc = _to_doc(ad, s)
    # Try up to 3 image candidates — the first can be hotlink-blocked or a
    # dead variant while the second mirrors fine.
    candidates = [u for u in ad.images[:3] if u]
    if candidates and r2_enabled():
        async with sem:
            for src in candidates:
                # key prefix "media/" (NOT "ads/") — ad blockers block /ads/ URLs too
                r2_url = await mirror_to_r2(src, f"media/{ad.ad_id}.jpg")
                if r2_url:
                    doc["media_urls"] = [r2_url] + [u for u in doc["media_urls"] if u != src]
                    doc["thumbnail"] = r2_url
                    break
        if "thumbnail" not in doc:
            # Mirror failed everywhere — a fresh signed FB URL still renders
            # for days; strictly better than shipping no thumbnail at all.
            doc["thumbnail"] = candidates[0]
    elif candidates:
        doc["thumbnail"] = candidates[0]

    # Heat is computed here (not in _to_doc) because it factors in whether
    # we actually have a creative to show.
    heat, velocity, momentum = compute_heat(
        days=s.days_running,
        variants=s.variant_count,
        ecom_signals=s.ecom_signals,
        strong_commerce=s.strong_commerce,
        is_active=doc.get("is_active", True),
        has_media=bool(doc.get("thumbnail")),
    )
    doc["heat"] = heat
    doc["velocity"] = velocity
    doc["momentum"] = momentum

    # Honest spend estimate (wide band, labeled). Upgraded in place to a
    # reach-based figure for EU ads when enrichment data is available.
    lo, hi, basis = estimate_spend(
        ad.country, s.days_running, s.variant_count, velocity=velocity
    )
    doc["est_spend_min_usd"] = lo
    doc["est_spend_max_usd"] = hi
    doc["spend_basis"] = basis
    return doc


async def _merge_existing(es, docs: list[dict]) -> dict[str, dict]:
    """Preserve cross-market identity on upsert; return the PRIOR state.

    `es.index(id=ad_id)` replaces the whole doc, so an ad seen first in SA and
    later by the KW sweep used to *become* a KW ad. Instead: keep the original
    `country` (first market we saw it in) and grow the `countries` list — the
    catalog compounds instead of churning.

    The returned {ad_id: previous _source} map is the last look at pre-upsert
    state — Trend Radar diffs against it (momentum flips, trend arrivals).
    """
    ids = [d["ad_id"] for d in docs]
    if not ids:
        return {}
    try:
        res = await es.mget(index="ads", body={"ids": ids})
    except Exception as e:  # noqa: BLE001 — merge is best-effort, never fail a sweep
        logger.warning("countries merge skipped (mget failed): %s", e)
        return {}
    existing = {d["_id"]: d.get("_source", {}) for d in res.get("docs", []) if d.get("found")}
    for doc in docs:
        old = existing.get(doc["ad_id"])
        if not old:
            continue
        merged = set(doc.get("countries") or [doc["country"]])
        merged.update(old.get("countries") or [])
        if old.get("country"):
            merged.add(old["country"])
            doc["country"] = old["country"]  # first-seen market stays primary
        doc["countries"] = sorted(merged)
    return existing


async def dive_and_index_brand(
    es,
    page_id: str,
    page_name: str,
    country: str,
    sem: asyncio.Semaphore,
    radar_events: Optional[list[dict]] = None,
    source: str = "brand_deepdive",
    max_keep: Optional[int] = None,
) -> tuple[int, int]:
    """Pull ONE brand's full live Ad Library catalog and index its winners.

    The shared per-brand engine behind both the sweep's deep-dive (brands it
    surfaced) and the Brand Hunter (brands discovered from live viral signals).
    Returns (catalog_indexed, live_ad_count). Records a BrandSnapshot and, when
    `radar_events` is passed, escalation/expansion signals. `country` is the
    market catalog ads get attributed to (the ALL-countries fetch tags "ALL").
    """
    max_keep = max_keep or int(getattr(settings, "INGEST_DEEPDIVE_MAX_KEEP", 30))
    now_ts = int(datetime.now(timezone.utc).timestamp())

    ads, live = await fetch_page_ads(page_id, country=country)
    if not ads and not live:
        return 0, 0

    # Snapshot the observation (trajectory history). The previous snapshot,
    # read before inserting, feeds the radar's brand-escalation signal.
    prev_live = 0
    try:
        async with async_session() as db:
            prev_live = await db.scalar(
                select(BrandSnapshot.live_ads)
                .where(BrandSnapshot.page_id == page_id)
                .order_by(BrandSnapshot.captured_at.desc())
                .limit(1)
            ) or 0
            db.add(BrandSnapshot(
                page_id=page_id, page_name=page_name, country="ALL", live_ads=live,
            ))
            await db.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning("brand snapshot insert failed for %s: %s", page_name, e)
    if radar_events is not None:
        esc = brand_escalation_event(page_id, page_name, prev_live, live)
        if esc:
            radar_events.append(esc)

    # The brand's catalog ads join the index through the SAME winner filter
    # as sweep ads. Attribute ALL-countries ads to the market we care about.
    for ad in ads:
        if ad.country == "ALL":
            ad.country = country
    uniq = list({ad.ad_id: ad for ad in ads}.values())
    _assign_variant_counts(uniq)
    kept = [(ad, s) for ad in uniq if (s := score_ad(ad, now_ts)).keep]
    # Distinct creatives only — page catalogs are collation-heavy; the budget
    # must buy N different ads, not N copies of one.
    kept = _dedupe_creatives(kept)
    kept.sort(key=lambda t: t[1].score, reverse=True)
    kept = kept[:max_keep]

    docs = await asyncio.gather(*[_build_doc(ad, s, sem) for ad, s in kept])
    for d in docs:
        d["brand_live_ads"] = live
        d["source"] = source
    dive_prior = await _merge_existing(es, docs)
    for d in docs:
        await es.index(index="ads", id=d["ad_id"], document=d)

    # Radar: a RE-observed brand shipping a batch of fresh winners is a signal
    # (first observation excluded — everything is "new" then).
    if radar_events is not None and prev_live > 0:
        fresh = sum(1 for d in docs if d["ad_id"] not in dive_prior)
        exp = brand_expansion_event(page_id, page_name, country, fresh)
        if exp:
            radar_events.append(exp)

    # Stamp the live-ad count on the brand's PREVIOUSLY indexed ads too, so
    # Brand Spy's "N ads live" covers the whole footprint.
    try:
        await es.update_by_query(
            index="ads",
            body={
                "query": {"bool": {"filter": [{"term": {"advertiser_id": page_id}}]}},
                "script": {"source": "ctx._source.brand_live_ads = params.n",
                           "params": {"n": live}},
                "conflicts": "proceed",
            },
            refresh=True,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("brand_live_ads stamp failed for %s: %s", page_name, e)

    logger.info("Dived %s (%s) [%s]: %s ads live, %s catalog winners indexed.",
                page_name, page_id, source, live, len(docs))
    return len(docs), live


async def _deep_dive_pass(
    es,
    final: list[tuple[RawAd, object]],
    radar_events: Optional[list[dict]] = None,
) -> dict:
    """Brand deep-dive: for the hardest-scaling brands this sweep surfaced,
    pull their FULL live catalog by page_id.

    Per brand this yields: (a) the real "N ads live right now" count — the
    GetHookd-style brand-strength signal a keyword sweep can never see, (b) a
    BrandSnapshot row (trajectory history), and (c) their best catalog ads
    joining the index, which grows the pool with exactly the right ads.
    """
    stats = {"brands": 0, "catalog_indexed": 0}
    if not getattr(settings, "INGEST_DEEPDIVE_ENABLED", True):
        return stats
    min_variants = int(getattr(settings, "INGEST_DEEPDIVE_MIN_VARIANTS", 5))
    per_sweep = int(getattr(settings, "INGEST_DEEPDIVE_PER_SWEEP", 8))
    max_keep = int(getattr(settings, "INGEST_DEEPDIVE_MAX_KEEP", 30))
    cooldown_h = int(getattr(settings, "INGEST_DEEPDIVE_COOLDOWN_HOURS", 24))

    # Candidates: one entry per page, qualified by their hardest-scaling ad.
    by_page: dict[str, tuple[RawAd, object]] = {}
    for ad, s in final:
        if not ad.page_id or s.variant_count < min_variants:
            continue
        best = by_page.get(ad.page_id)
        if best is None or s.score > best[1].score:
            by_page[ad.page_id] = (ad, s)
    if not by_page:
        return stats

    # Skip brands dived within the cooldown window (snapshot spam + FB load).
    recent: set[str] = set()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=cooldown_h)
        async with async_session() as db:
            rows = await db.execute(
                select(BrandSnapshot.page_id).where(
                    BrandSnapshot.page_id.in_(list(by_page)),
                    BrandSnapshot.captured_at >= since,
                )
            )
            recent = {r[0] for r in rows.all()}
    except Exception as e:  # noqa: BLE001
        logger.warning("deep-dive cooldown check failed (diving anyway): %s", e)

    candidates = sorted(
        (t for pid, t in by_page.items() if pid not in recent),
        key=lambda t: t[1].score,
        reverse=True,
    )[:per_sweep]

    sem = asyncio.Semaphore(8)
    for seed_ad, _seed_score in candidates:
        indexed, _live = await dive_and_index_brand(
            es, seed_ad.page_id, seed_ad.page_name, seed_ad.country, sem,
            radar_events=radar_events, source="brand_deepdive", max_keep=max_keep,
        )
        if indexed or _live:
            stats["brands"] += 1
            stats["catalog_indexed"] += indexed
        await asyncio.sleep(random.uniform(2.0, 4.0))  # gentle on the FB session

    if stats["catalog_indexed"]:
        await es.indices.refresh(index="ads")
    return stats


async def ingest_best_performing(
    countries: Optional[Iterable[str]] = None,
    search_terms: Optional[Iterable[str]] = None,
    limit_per_query: int = 60,
    max_per_country: Optional[int] = None,
) -> dict:
    """
    Run one full ingestion sweep and index the best-performing ads.

    Returns stats: {fetched, unique, kept, dropped_spam, dropped_low_perf,
    indexed, per_country, top}.
    """
    countries = list(countries) if countries else sweep_countries()
    # Explicit terms (API/env) override for ALL countries; otherwise each
    # country gets its own language-appropriate category set.
    explicit_terms = (
        list(search_terms) if search_terms
        else (_as_list(getattr(settings, "INGEST_SEARCH_TERMS", None), []) or None)
    )
    max_per_country = max_per_country or int(getattr(settings, "INGEST_MAX_PER_COUNTRY", 40))

    # One sweep at a time — the core and global scheduler jobs (and manual
    # triggers) share the same FB session and the same LAST_RUN slot.
    async with _SWEEP_LOCK:
        # Clear the previous run's stats/alert so mid-run polling never shows stale data.
        LAST_RUN.update(
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            finished_at=None,
            stats=None,
            alert=None,
        )
        try:
            return await _run_sweep(countries, explicit_terms, limit_per_query, max_per_country)
        except Exception as e:
            # Without this, a crash leaves status stuck on "running" forever.
            LAST_RUN.update(
                status="error",
                finished_at=datetime.now(timezone.utc).isoformat(),
                alert=f"Sweep crashed: {e}",
            )
            raise


_SWEEP_LOCK = asyncio.Lock()


async def _run_sweep(
    countries: list[str],
    explicit_terms: Optional[list[str]],
    limit_per_query: int,
    max_per_country: int,
) -> dict:
    # 1) Scrape every (country, term). Dedup by ad_id as we go.
    by_id: dict[str, RawAd] = {}
    fetched = 0
    queries = 0
    for country in countries:
        terms = explicit_terms if explicit_terms else default_terms_for(country)
        for term in terms:
            ads = await fetch_ads(country=country, search_term=term, limit=limit_per_query)
            fetched += len(ads)
            queries += 1
            for ad in ads:
                by_id.setdefault(ad.ad_id, ad)
            await asyncio.sleep(0.5)  # gentle pacing between queries

    unique_ads = list(by_id.values())

    # 2) Scaling signal needs the full set, so count variants before scoring.
    _assign_variant_counts(unique_ads)

    # 3) Score + filter.
    now_ts = int(datetime.now(timezone.utc).timestamp())
    kept: list[tuple[RawAd, object]] = []
    dropped_spam = dropped_low_perf = 0
    for i, ad in enumerate(unique_ads):
        s = score_ad(ad, now_ts)
        if getattr(settings, "DEBUG", False) and i < 5:  # diagnostics: see why ads pass/fail
            logger.info("score: days=%s var=%s ecom=%s is_ecom=%s spam=%s keep=%s :: %s",
                        s.days_running, s.variant_count, s.ecom_signals, s.is_ecommerce,
                        s.spam_reason or "-", s.keep, ad.page_name[:30])
        if s.spam_reason:
            dropped_spam += 1
        elif not s.keep:
            dropped_low_perf += 1
        else:
            kept.append((ad, s))

    # 4) Rank by score, cap per country (keep only the very best per market —
    # trend markets get their own, lower cap). Dedupe to one doc per creative
    # per market first, so cap slots buy distinct winners, never collated copies.
    kept = _dedupe_creatives(kept)
    kept.sort(key=lambda t: t[1].score, reverse=True)
    per_country_count: dict[str, int] = {}
    final: list[tuple[RawAd, object]] = []
    for ad, s in kept:
        if per_country_count.get(ad.country, 0) >= cap_for(ad.country, max_per_country):
            continue
        per_country_count[ad.country] = per_country_count.get(ad.country, 0) + 1
        final.append((ad, s))

    # 5) Mirror the lead creative to R2 (persistent thumbnails), then upsert to ES.
    sem = asyncio.Semaphore(8)
    docs = await asyncio.gather(*[_build_doc(ad, s, sem) for ad, s in final])

    # EU reach enrichment: for EU markets the official DSA API publishes REAL
    # reach per ad — join by ad_archive_id and upgrade those spend estimates.
    # No-op while META_ACCESS_TOKEN is missing/expired.
    eu_swept = [c for c in countries if c in EU_COUNTRIES]
    if eu_swept and any(d.get("country") in EU_COUNTRIES for d in docs):
        reach_map: dict[str, int] = {}
        for c in eu_swept:
            for term in (explicit_terms if explicit_terms else default_terms_for(c)):
                reach_map.update(await fetch_eu_reach(c, term))
        if reach_map:
            for d in docs:
                apply_reach_to_doc(d, reach_map)
            enriched = sum(1 for d in docs if d.get("eu_total_reach"))
            logger.info("EU reach enrichment: real reach on %s ads.", enriched)

    indexed = 0
    marked_inactive = 0
    deepdive_stats = {"brands": 0, "catalog_indexed": 0}
    es = get_es_client()
    try:
        await setup_index(es)
        # An ad re-seen from another market keeps its identity (country list
        # grows) instead of being overwritten as a fresh single-country doc.
        # The prior-state map feeds Trend Radar's diffing below.
        prior = await _merge_existing(es, docs)
        for doc in docs:
            await es.index(index="ads", id=doc["ad_id"], document=doc)
            indexed += 1
        if indexed:
            await es.indices.refresh(index="ads")

        # Brand deep-dive: full catalogs + live-ad counts for the top scalers.
        radar_events: list[dict] = []
        try:
            deepdive_stats = await _deep_dive_pass(es, final, radar_events)
        except Exception as e:  # noqa: BLE001 — never fail the sweep on the extra pass
            logger.warning("Brand deep-dive pass failed: %s", e)

        # Trend Radar: diff this sweep against prior state → market signals.
        core_markets = set(_as_list(getattr(settings, "INGEST_COUNTRIES", None), DEFAULT_COUNTRIES))
        radar_events.extend(detect_ad_events(prior, docs, core_markets))
        radar_written = await record_events(radar_events)

        # 6) Freshness pass: re-indexed ads got a new indexed_at above; anything
        # still-active that no sweep has re-seen in INGEST_STALE_DAYS is
        # presumed dead and flipped inactive, so "active"/"longest running"
        # stays honest instead of frozen at first-scrape time.
        stale_days = int(getattr(settings, "INGEST_STALE_DAYS", 14))
        try:
            resp = await es.update_by_query(
                index="ads",
                body={
                    "conflicts": "proceed",
                    "query": {"bool": {"filter": [
                        {"term": {"is_active": True}},
                        {"range": {"indexed_at": {"lt": f"now-{stale_days}d"}}},
                    ]}},
                    "script": {"source": "ctx._source.is_active = false"},
                },
                refresh=True,
            )
            marked_inactive = int(resp.get("updated", 0))
            if marked_inactive:
                logger.info("Freshness pass: marked %s stale ads inactive (>%sd unseen).",
                            marked_inactive, stale_days)
        except Exception as e:  # noqa: BLE001 — freshness is best-effort, never fail the sweep
            logger.warning("Freshness pass failed: %s", e)
    finally:
        await es.close()

    stats = {
        "fetched": fetched,
        "unique": len(unique_ads),
        "kept": len(final),
        "dropped_spam": dropped_spam,
        "dropped_low_perf": dropped_low_perf,
        "indexed": indexed,
        "marked_inactive": marked_inactive,
        "brands_deepdived": deepdive_stats["brands"],
        "catalog_indexed": deepdive_stats["catalog_indexed"],
        "radar_events": radar_written,
        "per_country": per_country_count,
        "top": [
            {"advertiser": ad.page_name, "country": ad.country,
             "days_running": s.days_running, "variants": s.variant_count, "score": s.score}
            for ad, s in final[:10]
        ],
    }

    # Dead-session detection: HTTP succeeded but zero ads across the whole sweep
    # almost always means the cookie/tokens died (FB returns empty or an error
    # envelope). Surface it loudly instead of letting the catalog rot silently.
    alert = None
    if fetched == 0 and queries:
        alert = (
            f"Sweep fetched 0 ads across {queries} queries — the Facebook session is "
            "likely dead or expired. Open the Ingestion page and paste a fresh cookie."
        )
        logger.warning(alert)

    LAST_RUN.update(
        status="ok",
        finished_at=datetime.now(timezone.utc).isoformat(),
        stats=stats,
        alert=alert,
    )
    logger.info("Ingestion sweep done: %s", {k: stats[k] for k in (
        "fetched", "unique", "kept", "indexed", "marked_inactive",
        "brands_deepdived", "catalog_indexed")})
    return stats
