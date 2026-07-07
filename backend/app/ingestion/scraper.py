"""
Meta Ad Library scraper.

Unlike the official `ads_archive` Graph API (which only exposes political/issue
ads outside the EU/UK), the public Ad Library web app at
https://www.facebook.com/ads/library/ shows the FULL commercial library for
every country — including MENA. This module talks to the same private endpoint
the web app uses (`/ads/library/async/search_ads/`), which returns structured
JSON with creative copy, images and videos.

⚠️  This is scraping. It is against Meta's ToS, it can break whenever Meta
changes their internal API, and it needs a logged-in session:

    META_FB_COOKIE   - the full Cookie header from a logged-in facebook.com
                       session (must include c_user and xs)
    META_FB_DTSG     - the fb_dtsg token from the same session (optional but
                       strongly recommended; without it FB often returns empty)
    SCRAPER_PROXY    - optional http(s) proxy, e.g. http://user:pass@host:port

Set these in backend/.env. Without valid cookies the endpoint returns no
results and the pipeline simply ingests nothing (it never crashes the app).
"""

import asyncio
import json
import logging
import os
import random
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qsl

import httpx

from app.core.config import settings
from app.ingestion.session import FBSession, get_session

logger = logging.getLogger("adspy.scraper")

SEARCH_URL = "https://www.facebook.com/ads/library/async/search_ads/"
GRAPHQL_URL = "https://www.facebook.com/api/graphql/"

# Where we persist the captured Ad Library GraphQL request template.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_FILE = os.path.join(_BACKEND_DIR, ".adlib_query.json")

# A normal desktop UA. Meta serves the async endpoint to logged-in browsers.
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


@dataclass
class RawAd:
    """A single ad as scraped from the Ad Library, before scoring/mapping."""

    ad_id: str
    page_id: str
    page_name: str
    body_text: str = ""
    title: str = ""
    caption: str = ""
    cta_text: str = ""
    link_url: str = ""
    images: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None
    is_active: bool = True
    publisher_platforms: list[str] = field(default_factory=list)
    country: str = ""
    snapshot_url: str = ""
    # variant_count = Meta's collation_count (scaling); refined by the pipeline.
    variant_count: int = 1
    total_active_secs: int = 0  # ad lifetime in seconds (Meta total_active_time)

    @property
    def primary_text(self) -> str:
        """Best available text for search / spam-classification."""
        return (self.body_text or self.title or self.caption or self.page_name).strip()


def _headers(sess: FBSession) -> dict:
    return {
        "User-Agent": getattr(settings, "SCRAPER_USER_AGENT", "") or _DEFAULT_UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,ar;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": sess.cookie,
        "X-FB-LSD": sess.lsd,
        "Origin": "https://www.facebook.com",
        "Referer": "https://www.facebook.com/ads/library/",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }


def _form(country: str, search_term: str, cursor: Optional[str], count: int, sess: FBSession) -> dict:
    """Build the POST body for the async search endpoint."""
    form = {
        "session_id": "%032x" % random.getrandbits(128),
        "count": str(count),
        "active_status": "active",
        "ad_type": "all",
        "countries[0]": country,
        "media_type": "all",
        "search_type": "keyword_unordered" if search_term else "page",
        "q": search_term or "",
        "sort_data[direction]": "desc",
        "sort_data[mode]": "relevancy_monthly_grouped",
        # session tokens (FB rejects the call without these on most accounts)
        "__a": "1",
        "fb_dtsg": sess.fb_dtsg,
        "lsd": sess.lsd,
    }
    if cursor:
        form["forward_cursor"] = cursor
    return form


def _strip_prefix(text: str) -> str:
    """Meta prefixes JSON with `for (;;);` to thwart hijacking. Strip it."""
    text = text.lstrip()
    if text.startswith("for (;;);"):
        return text[len("for (;;);"):]
    return text


def _first(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _parse_ad(node: dict, country: str) -> Optional[RawAd]:
    """Map one raw Ad Library node into a RawAd. Defensive about key names."""
    snap = node.get("snapshot") or {}
    ad_id = str(_first(node, "adArchiveID", "ad_archive_id", "adArchiveId", default="") or "")
    if not ad_id:
        return None

    body = snap.get("body") or {}
    body_text = body.get("text") if isinstance(body, dict) else (body or "")

    images, videos = [], []
    for img in (snap.get("images") or []):
        url = _first(img, "original_image_url", "resized_image_url")
        if url:
            images.append(url)
    for vid in (snap.get("videos") or []):
        # the preview image is the thumbnail we want to show for video ads
        preview = _first(vid, "video_preview_image_url")
        if preview:
            images.append(preview)
        url = _first(vid, "video_hd_url", "video_sd_url")
        if url:
            videos.append(url)
    # carousel cards carry their own media + copy
    for card in (snap.get("cards") or []):
        url = _first(card, "original_image_url", "resized_image_url", "video_preview_image_url")
        if url:
            images.append(url)
        vurl = _first(card, "video_hd_url", "video_sd_url")
        if vurl:
            videos.append(vurl)

    return RawAd(
        ad_id=ad_id,
        page_id=str(_first(node, "pageID", "page_id", default="") or ""),
        page_name=_first(node, "pageName", "page_name", default="") or snap.get("page_name", "") or "Unknown",
        body_text=(body_text or "").strip(),
        title=(snap.get("title") or "").strip(),
        caption=(snap.get("caption") or "").strip(),
        cta_text=(snap.get("cta_text") or "").strip(),
        link_url=(snap.get("link_url") or "").strip(),
        images=images,
        videos=videos,
        start_ts=_first(node, "startDate", "start_date"),
        end_ts=_first(node, "endDate", "end_date"),
        is_active=bool(_first(node, "isActive", "is_active", default=True)),
        publisher_platforms=_first(node, "publisherPlatform", "publisher_platform", default=[]) or [],
        country=country,
        snapshot_url=f"https://www.facebook.com/ads/library/?id={ad_id}",
        # collation_count = how many copies of this creative the advertiser runs
        # (Meta's own scaling signal). total_active_time = lifetime in seconds.
        variant_count=int(_first(node, "collation_count", "collationCount", default=1) or 1),
        total_active_secs=int(_first(node, "total_active_time", "totalActiveTime", default=0) or 0),
    )


def _extract_nodes(payload: dict) -> list[dict]:
    """Pull the flat list of ad nodes out of the (nested) results structure."""
    results = payload.get("results") or payload.get("ads") or []
    nodes: list[dict] = []
    for group in results:
        # `results` is usually a list of collated groups (each a list of ads)
        if isinstance(group, list):
            nodes.extend(g for g in group if isinstance(g, dict))
        elif isinstance(group, dict):
            nodes.append(group)
    return nodes


# ─── GraphQL capture-and-replay ─────────────────────────────────────────────
# Meta retired /ads/library/async/search_ads/ (it 404s now). The live Ad Library
# uses /api/graphql/ with a rotating doc_id we can't guess. So the user captures
# their browser's real search request once ("Copy as cURL", pasted into the app —
# never into chat), and we replay it with the live session + substituted
# country / keyword / cursor. Re-capture if Meta rotates the doc_id.

def _parse_curl_body(curl_text: str) -> Optional[str]:
    """Extract the POST body (--data-raw / --data / -d ...) from a 'Copy as cURL' blob."""
    for flag in ("--data-raw", "--data-binary", "--data", "-d"):
        idx = curl_text.find(flag)
        if idx == -1:
            continue
        rest = curl_text[idx + len(flag):].lstrip()
        if not rest:
            continue
        if rest[0] in "'\"":
            quote = rest[0]
            rest = rest[1:]
            end = rest.find(quote)
            return rest[:end] if end != -1 else rest
        return rest.split()[0]  # unquoted (rare)
    return None


def _save_template(template: dict) -> None:
    try:
        with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
            json.dump(template, f)
    except OSError as e:
        logger.warning("Could not save search template: %s", e)


def _load_template() -> Optional[dict]:
    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def has_search_template() -> bool:
    return os.path.exists(TEMPLATE_FILE)


def import_search_template(curl_text: str) -> Optional[dict]:
    """Parse a captured Ad Library GraphQL 'Copy as cURL' into a replay template."""
    body = _parse_curl_body(curl_text or "")
    if not body:
        return None
    params = dict(parse_qsl(body, keep_blank_values=True))
    if "variables" not in params or "doc_id" not in params:
        return None
    try:
        variables = json.loads(params["variables"])
    except (ValueError, TypeError):
        return None
    template = {
        "doc_id": params.get("doc_id", ""),
        "friendly_name": params.get("fb_api_req_friendly_name", "AdLibrarySearchPaginationQuery"),
        "params": params,        # full body; session fields overridden at replay time
        "variables": variables,  # parsed; mutated per query
    }
    _save_template(template)
    logger.info("Saved Ad Library search template (doc_id=%s, friendly=%s).",
                template["doc_id"], template["friendly_name"])
    return template


def _mutate_variables(
    variables: dict,
    country: str,
    term: str,
    cursor: Optional[str],
    limit: int,
    page_id: str = "",
) -> dict:
    """Turn the captured request into a fresh search for one country.

    Two modes:
      • keyword (default) — neutralizes any *page pin* from the capture: if the
        user grabbed the request while viewing one advertiser, `searchType="page"`
        + `viewAllPageID=<that page>` would force every result to that page. We
        reset those so the term/country actually drive results.
      • page (`page_id` set) — deliberately pins to one advertiser to pull their
        FULL live catalog (the brand deep-dive). Same mechanism, on purpose.
    """
    v = dict(variables)
    v["countries"] = [country]
    if "queryString" in v or "query" not in v:
        v["queryString"] = "" if page_id else term
    else:
        v["query"] = "" if page_id else term
    if page_id:
        v["searchType"] = "page"
        v["viewAllPageID"] = page_id
        if "pageIDs" in v:
            v["pageIDs"] = [page_id]
    else:
        # force keyword search, drop any pinned page
        v["searchType"] = "keyword_unordered"
        if "viewAllPageID" in v:
            v["viewAllPageID"] = "0"
        if "pageIDs" in v:
            v["pageIDs"] = []
    if "first" in v:
        v["first"] = min(limit, 30)
    elif "count" in v:
        v["count"] = min(limit, 30)
    v["cursor"] = cursor
    v["excludedIDs"] = []
    # fresh session id per query so pagination/grouping doesn't carry over
    if "sessionID" in v:
        v["sessionID"] = str(uuid.uuid4())
    return v


def _graphql_nodes(data: dict) -> list[dict]:
    """Pull ad nodes out of an AdLibrarySearch GraphQL response."""
    try:
        conn = data["data"]["ad_library_main"]["search_results_connection"]
    except (KeyError, TypeError):
        return []
    nodes: list[dict] = []
    for edge in conn.get("edges", []):
        node = (edge or {}).get("node") or {}
        collated = node.get("collated_results") or [node]
        nodes.extend(c for c in collated if isinstance(c, dict))
    return nodes


def _graphql_page_info(data: dict) -> dict:
    try:
        return data["data"]["ad_library_main"]["search_results_connection"].get("page_info", {})
    except (KeyError, TypeError):
        return {}


def _graphql_total(data: dict) -> Optional[int]:
    """Meta's own result count for the search, when the response carries one.

    For a page-pinned search this is the advertiser's TOTAL live-ad count — the
    number the Ad Library UI shows as "~N results" — which is exactly the
    "brand runs 50+ ads" signal. Key names drift, so probe the known variants.
    """
    try:
        main = data["data"]["ad_library_main"]
    except (KeyError, TypeError):
        return None
    conn = main.get("search_results_connection") or {}
    for holder, key in ((conn, "count"), (conn, "total_count"),
                        (main, "search_results_count"), (main, "total_result_count")):
        val = holder.get(key)
        if isinstance(val, int) and val >= 0:
            return val
    return None


def _graphql_headers(sess: FBSession, friendly: str) -> dict:
    return {
        "User-Agent": getattr(settings, "SCRAPER_USER_AGENT", "") or _DEFAULT_UA,
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": sess.cookie,
        "X-FB-Friendly-Name": friendly,
        "X-FB-LSD": sess.lsd,
        "Origin": "https://www.facebook.com",
        "Referer": "https://www.facebook.com/ads/library/",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }


async def _fetch_graphql(
    sess: FBSession,
    country: str,
    search_term: str,
    limit: int,
    max_pages: int,
    page_id: str = "",
) -> tuple[list[RawAd], Optional[int]]:
    """Returns (ads, meta_total). meta_total is Meta's own result count when the
    response exposes one (page-pinned searches use it as the live-ad count)."""
    template = _load_template()
    if not template:
        return [], None
    proxy = getattr(settings, "SCRAPER_PROXY", "") or None
    friendly = template.get("friendly_name", "AdLibrarySearchPaginationQuery")
    out: list[RawAd] = []
    meta_total: Optional[int] = None
    cursor: Optional[str] = None
    logged = False
    refreshed = False

    async with httpx.AsyncClient(timeout=45, proxy=proxy, follow_redirects=True) as client:
        for _page in range(max_pages):
            params = dict(template["params"])
            params["fb_dtsg"] = sess.fb_dtsg or params.get("fb_dtsg", "")
            if sess.lsd:
                params["lsd"] = sess.lsd
            if sess.user_id:
                params["__user"] = sess.user_id
            params["doc_id"] = template["doc_id"]
            params["variables"] = json.dumps(
                _mutate_variables(template["variables"], country, search_term, cursor, limit, page_id)
            )
            try:
                resp = await client.post(GRAPHQL_URL, headers=_graphql_headers(sess, friendly), data=params)
            except httpx.HTTPError as e:
                logger.warning("GraphQL request failed (%s/%s): %s", country, search_term, e)
                break
            if resp.status_code != 200:
                logger.warning("GraphQL status=%s for %s/'%s'.", resp.status_code, country, search_term)
                break
            try:
                data = json.loads(_strip_prefix(resp.text))
            except json.JSONDecodeError:
                logger.warning("GraphQL non-JSON for %s/'%s' (login wall / stale doc_id?).", country, search_term)
                break
            # Facebook rejects a stale fb_dtsg with a 200 + {error, errorSummary}
            # envelope (e.g. 1357004) — NOT the GraphQL `errors` key. Catch it,
            # refresh the session once, and retry the same page.
            if isinstance(data, dict) and data.get("error") and not data.get("data"):
                logger.warning("GraphQL FB error for %s/'%s': %s / %s",
                               country, search_term, data.get("error"), data.get("errorSummary"))
                if not refreshed:
                    refreshed = True
                    sess = await get_session(force=True) or sess
                    continue
                break
            nodes = _graphql_nodes(data)
            if meta_total is None:
                meta_total = _graphql_total(data)
            if not logged:
                if data.get("errors"):
                    logger.warning("GraphQL errors for %s/'%s': %s", country, search_term,
                                   json.dumps(data["errors"])[:300])
                if getattr(settings, "DEBUG", False) and nodes:
                    logger.info("GraphQL node keys (%s/'%s'): %s", country, search_term, list(nodes[0].keys()))
                logged = True
            for node in nodes:
                ad = _parse_ad(node, country)
                if ad:
                    out.append(ad)
            if len(out) >= limit:
                break
            pi = _graphql_page_info(data)
            cursor = pi.get("end_cursor")
            if not cursor or not pi.get("has_next_page"):
                break
            await asyncio.sleep(random.uniform(1.5, 3.5))

    logger.info("Scraped %d ads (graphql) for %s/'%s'%s", len(out), country,
                search_term or (f"page:{page_id}" if page_id else ""),
                f" (meta_total={meta_total})" if meta_total is not None else "")
    return out[:limit], meta_total


async def fetch_page_ads(
    page_id: str,
    country: str = "ALL",
    limit: int = 90,
    max_pages: int = 4,
) -> tuple[list[RawAd], int]:
    """Brand deep-dive: pull one advertiser's FULL live ad catalog by page_id.

    Returns (ads, live_ad_count). The count prefers Meta's own total for the
    page-pinned search (the "~N results" the Ad Library UI shows); when the
    response doesn't expose one, it falls back to the number of ads fetched —
    a lower bound once the catalog exceeds `limit`.

    `country="ALL"` asks for the brand's global footprint; if Meta rejects that
    (0 results), we retry scoped to the given fallback country.
    """
    sess = await get_session()
    if sess is None or not has_search_template():
        return [], 0

    ads, meta_total = await _fetch_graphql(sess, "ALL", "", limit, max_pages, page_id=page_id)
    if not ads and country != "ALL":
        ads, meta_total = await _fetch_graphql(sess, country, "", limit, max_pages, page_id=page_id)
    live = meta_total if (meta_total is not None and meta_total >= len(ads)) else len(ads)
    return ads, live


async def resolve_page_id(
    name: str,
    country: str = "ALL",
    limit: int = 40,
) -> Optional[tuple[str, str]]:
    """Resolve an advertiser NAME to its Facebook page (page_id, page_name).

    The discovery unlock: a viral-brand name from ANY source (TikTok Creative
    Center, web research, a manual seed) is useless to the deep-dive without a
    page_id. So we keyword-search the Ad Library for the name and pick the page
    that (a) best matches the name and (b) runs the most ads under it — a real
    advertiser, not a one-off mention. Returns None when nothing plausibly
    matches (the brand may not run Meta ads, or the session is dead).
    """
    name = (name or "").strip()
    if len(name) < 2:
        return None
    ads = await fetch_ads(country=country, search_term=name, limit=limit, max_pages=1)
    if not ads:
        return None

    import difflib

    def norm(s: str) -> str:
        return re.sub(r"[^0-9a-z؀-ۿ]+", "", (s or "").lower())

    target = norm(name)
    # Group by page: how many ads, and the best name-similarity we saw.
    pages: dict[str, dict] = {}
    for ad in ads:
        if not ad.page_id:
            continue
        p = pages.setdefault(ad.page_id, {"name": ad.page_name, "count": 0, "sim": 0.0})
        p["count"] += 1
        pn = norm(ad.page_name)
        sim = 1.0 if (target and (target in pn or pn in target)) else \
            difflib.SequenceMatcher(None, target, pn).ratio()
        if sim > p["sim"]:
            p["sim"] = sim
            p["name"] = ad.page_name
    if not pages:
        return None

    # Require a real name match (guards against keyword-in-copy false hits),
    # then prefer the strongest match, breaking ties by ad volume.
    best_id = max(pages, key=lambda pid: (pages[pid]["sim"], pages[pid]["count"]))
    best = pages[best_id]
    if best["sim"] < 0.6:
        logger.info("resolve_page_id('%s'): best match '%s' sim=%.2f — rejected.",
                    name, best["name"], best["sim"])
        return None
    return best_id, best["name"]


async def fetch_live_count(country: str, search_term: str) -> Optional[int]:
    """Meta's own "~N results" total for a keyword search in one market —
    the truth behind any "nobody runs this there" claim (dossier gap map).

    One page, tiny limit; only an EXPLICIT total from the response counts.
    None means "couldn't verify" (dead session, missing total, block) — the
    caller must stay silent rather than claim an unverified zero.
    """
    if not search_term:
        return None
    sess = await get_session()
    if sess is None or not has_search_template():
        return None
    _ads, total = await _fetch_graphql(sess, country, search_term, limit=10, max_pages=1)
    return total


async def fetch_ads(
    country: str,
    search_term: str = "",
    limit: int = 60,
    max_pages: int = 3,
) -> list[RawAd]:
    """
    Scrape up to `limit` ads for one country/search term, paginating as needed.

    The Facebook session is resolved automatically (browser cookies / env / disk
    cache — see session.py). Returns [] (and logs a warning) if no session is
    available or Meta blocks the request — never raises, so the scheduler keeps
    running. On a likely-auth failure it refreshes the session once and retries.
    """
    sess = await get_session()
    if sess is None:
        logger.warning(
            "Ad Library scrape skipped: no Facebook session available "
            "(log into facebook.com in your browser, or set META_FB_COOKIE)."
        )
        return []

    # Preferred path: replay the captured GraphQL request (the live endpoint).
    if has_search_template():
        ads, _total = await _fetch_graphql(sess, country, search_term, limit, max_pages)
        return ads

    logger.warning(
        "No Ad Library search template captured — the legacy endpoint is dead (404). "
        "Capture your browser's search request on the Ingestion page (Copy as cURL)."
    )

    proxy = getattr(settings, "SCRAPER_PROXY", "") or None
    count = min(limit, 30)
    out: list[RawAd] = []
    cursor: Optional[str] = None
    refreshed = False

    async with httpx.AsyncClient(timeout=45, proxy=proxy, follow_redirects=True) as client:
        page = 0
        while page < max_pages:
            try:
                resp = await client.post(
                    SEARCH_URL,
                    headers=_headers(sess),
                    data=_form(country, search_term, cursor, count, sess),
                )
            except httpx.HTTPError as e:
                logger.warning("Ad Library request failed (%s/%s): %s", country, search_term, e)
                break

            status = resp.status_code
            data = None
            if status == 200:
                try:
                    data = json.loads(_strip_prefix(resp.text))
                except json.JSONDecodeError:
                    data = None  # login wall / challenge returns HTML, not JSON

            if data is None:
                # 404/400 = wrong endpoint or params (Meta changed the API) —
                # refreshing tokens won't help, so don't hammer FB. Only an
                # auth-type failure (401/403, or 200-but-not-JSON login wall)
                # is worth one token refresh + retry.
                auth_failure = status in (401, 403) or status == 200
                if auth_failure and not refreshed:
                    logger.info("Ad Library auth issue (status=%s) — refreshing tokens, retrying.", status)
                    new = await get_session(force=True)
                    refreshed = True
                    if new is not None:
                        sess = new
                        continue
                if status in (404, 400):
                    logger.warning(
                        "Ad Library endpoint returned %s for %s/'%s' — the search API path "
                        "likely changed. Capture the live request and update SEARCH_URL/params.",
                        status, country, search_term,
                    )
                else:
                    logger.warning("Ad Library blocked for %s/'%s' (status=%s).", country, search_term, status)
                break

            payload = data.get("payload") or data
            for node in _extract_nodes(payload):
                ad = _parse_ad(node, country)
                if ad:
                    out.append(ad)

            if len(out) >= limit:
                break
            cursor = payload.get("forwardCursor") or payload.get("forward_cursor")
            if not cursor or payload.get("isResultComplete", True):
                break
            page += 1
            await asyncio.sleep(random.uniform(1.5, 3.5))  # be polite / avoid rate limits

    logger.info("Scraped %d ads for %s/'%s'", len(out), country, search_term)
    return out[:limit]
