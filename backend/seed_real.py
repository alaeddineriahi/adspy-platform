"""
Seed the Elasticsearch 'ads' index with REAL MENA ads pulled from Meta's
Ad Library (via the authorized Ad Library search).

Unlike seed.py (synthetic samples), every record here is a real, live ad that
was running in TN / AE / SA / EG / MA. Fields available from the Ad Library
search: id, page (name + id), creative link title, creation/delivery dates,
snapshot URL, currency. Full body copy and media files live behind each
snapshot URL and are not exposed by this endpoint, so copy_text falls back to
the ad's link title (or the page name when the title is blank).

Run:  venv/Scripts/python.exe seed_real.py
"""

import asyncio
import re
from datetime import datetime, timezone

from app.core.elasticsearch import get_es_client, setup_index


# Raw records as returned by the Meta Ad Library search, tagged with the
# country they were reached in. (id, page_id, page_name, title, created, start,
# currency, country)
RAW_ADS = [
    # ─── Tunisia ──────────────────────────────────────────────────────
    ("1015229254543089", "328556294207507", "Oneaday", "Huile bronzante + Huile SPF50 ✨☀️ 🎁", 1782667188, 1782669432, "USD", "TN"),
    ("2064637904166565", "103124611592202", "Meilleur goût", "Réparez et apaisez votre peau instantanément", 1782665473, 1782667544, "USD", "TN"),
    ("27545757418370012", "108730375250337", "Kwadeco", "Tableau sur toile de ville colorée effet peinture", 1782664926, 1782670316, "USD", "TN"),
    ("975639528623922", "946667628532729", "AVA.tn", "9 styles au choix - Livraison gratuite", 1782664814, 1782670426, "USD", "TN"),
    ("1566801888274093", "1012268275306224", "Piingoo", "Chic au travail, élégant en sortie", 1782660831, 1782668790, "USD", "TN"),
    ("1660761805220579", "103384579225975", "am_store_tn", "", 1782669662, 1782671678, "USD", "TN"),
    ("2143899812827792", "103808080984836", "Meuble déco", "", 1782666408, 1782671406, "USD", "TN"),
    ("1699579644300728", "418018528065351", "Nova Meubles", "", 1782664936, 1782670160, "EUR", "TN"),
    ("2237047496834485", "1691634464425360", "F mejri rent car", "", 1782664547, 1782669896, "USD", "TN"),
    ("1002897202267830", "1053917321142958", "GlobalLing", "🌍Talk to Anyone, Anywhere", 1777799349, 1777834200, "USD", "TN"),
    ("4753934418214515", "112199730199073", "GERAJEUNE", "Trouvez le soin adapté parmi toute la gamme Gerajeune.", 1782580319, 1782586671, "USD", "TN"),
    ("1031437942617002", "711219182084491", "Loving Romance Forever", "Le Regret de l'Alpha Quand Je Veux un Divorce", 1782574266, 1782583625, "USD", "TN"),
    ("2888588514817580", "581989108327626", "PURE PARA", "Parapharmacie en ligne - Chat with us", 1782567878, 1782572785, "EUR", "TN"),
    ("1349591860462953", "938485679345184", "Readfun", "😍Cliquez pour continuer la lecture <Juste Un Baiser, avant que tu me divorces>", 1782641950, 1782647529, "USD", "TN"),
    ("1305350941215541", "105394365996917", "Lanter Odyssey", "🚀 2025's #1 mobile game is live!", 1755238116, 1755336327, "USD", "TN"),
    ("2605276413160439", "127096143809427", "Lanter Odyssey", "💥Complete quests and boss battles to earn gold, diamonds, and gear.", 1755241830, 1755274226, "USD", "TN"),

    # ─── UAE ──────────────────────────────────────────────────────────
    ("2228679864561835", "687589164666184", "MasterClass", "Invest In Personal Growth", 1782451252, 1782497243, "USD", "AE"),
    ("1699587294315421", "954068831126233", "Dr. Seraphina", "Effective MicroNeedle BotanicSkinTag Removal Patch", 1782664289, 1782671448, "USD", "AE"),
    ("987438120857362", "106140462574984", "Fantasy Reading", "🔞Attention! Do not read in public！👉", 1782662902, 1782668796, "USD", "AE"),
    ("769430426177203", "726092743929980", "Romantic Lover", "Read Now 👉", 1767600880, 1768126711, "USD", "AE"),

    # ─── Saudi Arabia ─────────────────────────────────────────────────
    ("4641977099372171", "1095136270360302", "Darifa", "راسلنا الآن واستفسر مجانًا.", 1782639173, 1782671363, "SAR", "SA"),
    ("997722163332826", "107975038016683", "SOME APPS", "تطبيق مجاني ⭐⭐⭐⭐⭐", 1782657214, 1782671499, "VND", "SA"),
    ("2090172601894337", "1116824464848171", "مسلسلات قصيرة رائعة", "#Goodshort", 1782665374, 1782670924, "USD", "SA"),
    ("1866733357635045", "981239325071132", "دراما ممتازة", "#Goodshort", 1782665374, 1782670653, "USD", "SA"),
    ("1698838497708068", "603329342872044", "Creative Touch FZE", "", 1782665380, 1782671482, "AED", "SA"),

    # ─── Egypt ────────────────────────────────────────────────────────
    ("1547809686986746", "107048648579911", "oraimo store", "midnight-flash-sales", 1782618898, 1782662813, "USD", "EG"),
    ("2091794211720508", "588002194395358", "ادرس في مصر للوافدين", "دردشة في Messenger", 1782653647, 1782660502, "EGP", "EG"),
    ("995553379850253", "688022494404570", "Temu Egypt", "تعال وتسوق معنا", 1782652583, 1782662386, "USD", "EG"),
    ("1099019762621402", "784949171368634", "الموسكى شوب", "عرض الصيف (2*1) تخفيضات الصيف", 1782652158, 1782657695, "EGP", "EG"),
    ("1707088854754203", "501929476339427", "ماركت البان العميد", "", 1782656997, 1782662002, "EGP", "EG"),

    # ─── Morocco ──────────────────────────────────────────────────────
    ("2728514420855316", "113288623549171", "Criystele", "👑 Une Abaya Élégante pour Chaque Princesse", 1782573431, 1782649938, "USD", "MA"),
    ("2064139037840195", "1066457986558241", "Animalerie.saad", "💰 180 DH seulement 🚚 Livraison gratuite", 1782669193, 1782671130, "USD", "MA"),
    ("897059256769475", "1013881868480460", "Heyshop.ma", "رف مطبخ قابل للطي", 1782666429, 1782671652, "USD", "MA"),
    ("1994543854522465", "837248782810866", "ZK WEAR", "👇 اطلب الآن 👇", 1782578724, 1782657465, "USD", "MA"),
    ("2446933925802642", "100847249075220", "Zinati", "كوني انيقة، في كل مكان", 1782665181, 1782670168, "USD", "MA"),
    ("1525191142409389", "713259171864009", "Kissi.brand", "🕶️ KISSI UV400 Jour & Nuit", 1782664630, 1782670620, "USD", "MA"),
    ("1454030766778304", "355409990994564", "Styles Lunette", "Lunettes de Soleil Moscot Italiano Polarisées UV400 😎 Vintage Unisex 2025 | Livraison Gratuite", 1782664125, 1782665980, "USD", "MA"),
    ("4566193240279772", "872260609309117", "Alam.Brand", "alm luxx", 1782664871, 1782670288, "USD", "MA"),
]


_ARABIC_RE = re.compile(r"[؀-ۿ]")
_FRENCH_RE = re.compile(r"[éèàçùêâîôûÉÈÀ]|\b(le|la|les|de|des|du|pour|votre|gratuite|livraison|au|chez|et)\b", re.IGNORECASE)


def _detect_language(text: str, country: str) -> str:
    if _ARABIC_RE.search(text):
        return "ar"
    if _FRENCH_RE.search(text):
        return "fr"
    if country in ("TN", "MA", "DZ") and text.strip() and not text.isascii():
        return "fr"
    return "en"


def _iso(unix_ts: int) -> str:
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


def _days_running(start_ts: int) -> int:
    start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - start).days)


def _clean_title(title: str) -> str:
    # Ad Library repeats the link title once per carousel card joined by " | ".
    # Keep only the first, representative segment.
    if " | " in title:
        title = title.split(" | ")[0].strip()
    return title.strip()


def build_doc(raw) -> dict:
    ad_id, page_id, page_name, title, created, start, currency, country = raw
    title = _clean_title(title)
    copy_text = title if title and title not in ("instagram.com",) else page_name
    return {
        "ad_id": ad_id,
        "platform": "meta",
        "advertiser_name": page_name,
        "advertiser_id": page_id,
        "country": country,
        "language": _detect_language(copy_text, country),
        "ad_format": "image",  # Ad Library search doesn't expose creative type
        "copy_text": copy_text,
        "cta_text": "",
        "landing_page": f"https://www.facebook.com/ads/library/?id={ad_id}",
        "media_urls": [],  # only the snapshot page is available
        "snapshot_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
        "currency": currency,
        "first_seen": _iso(start),
        "last_seen": datetime.now(timezone.utc).isoformat(),
        "indexed_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "days_running": _days_running(start),
        "source": "meta_ad_library",
    }


async def main():
    es = get_es_client()
    try:
        await setup_index(es)
        per_country: dict[str, int] = {}
        for raw in RAW_ADS:
            doc = build_doc(raw)
            await es.index(index="ads", id=doc["ad_id"], document=doc)
            per_country[doc["country"]] = per_country.get(doc["country"], 0) + 1
        await es.indices.refresh(index="ads")
        count = await es.count(index="ads")
        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(per_country.items()))
        print(f"Seeded {len(RAW_ADS)} REAL Meta ads ({breakdown}).")
        print(f"Index 'ads' now has {count['count']} docs total.")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
