"""
Facebook session acquisition — so you don't paste a cookie every time.

Resolution order (first that works wins):
  1. Manual override   — META_FB_COOKIE in .env (+ optional META_FB_DTSG/LSD).
  2. Browser cookies   — read the live facebook.com session straight from the
                         browser you're already logged into on this machine
                         (Chrome / Edge / Firefox), via `browser-cookie3`.
  3. Disk cache        — the last good session we resolved (backend/.fb_session.json).

Whatever cookie we get, we bootstrap the page tokens (`fb_dtsg`, `lsd`) by
fetching the Ad Library page once and caching them for a few hours. If a scrape
later fails auth, the scraper calls invalidate() and we re-resolve automatically.

This means: log into Facebook in your browser once, and ingestion keeps working
— no copy-pasting. Set SCRAPER_USE_BROWSER_COOKIES=false to disable browser read.
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("adspy.session")

# backend/.fb_session.json  (this file lives at backend/app/ingestion/session.py)
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_FILE = os.path.join(_BACKEND_DIR, ".fb_session.json")

TOKEN_TTL = 3 * 3600  # re-bootstrap tokens after 3h; cookies are re-read each time

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

_cache: Optional["FBSession"] = None
_last_error: str = ""  # why browser cookie read failed, for the status endpoint

# Auto path order when SCRAPER_BROWSER=auto.
_BROWSER_ORDER = ["opera_gx", "opera", "chrome", "brave", "edge", "vivaldi", "chromium", "firefox"]


@dataclass
class FBSession:
    cookie: str
    fb_dtsg: str = ""
    lsd: str = ""
    user_id: str = ""
    source: str = ""          # "env" | "browser" | "disk"
    ts: float = 0.0

    def fresh(self) -> bool:
        return (time.time() - self.ts) < TOKEN_TTL


# ─── browser cookie extraction ─────────────────────────────────────────────

def _candidate_cookie_files(browser: str) -> list[str]:
    """Known Cookies-file locations per Chromium browser (handles the Default-profile layout)."""
    override = (getattr(settings, "SCRAPER_COOKIE_FILE", "") or "").strip()
    if override:
        return [override]

    appdata = os.environ.get("APPDATA", "")
    localapp = os.environ.get("LOCALAPPDATA", "")
    bases = {
        "opera_gx": [os.path.join(appdata, "Opera Software", "Opera GX Stable")],
        "opera": [os.path.join(appdata, "Opera Software", "Opera Stable")],
        "chrome": [os.path.join(localapp, "Google", "Chrome", "User Data")],
        "brave": [os.path.join(localapp, "BraveSoftware", "Brave-Browser", "User Data")],
        "edge": [os.path.join(localapp, "Microsoft", "Edge", "User Data")],
        "vivaldi": [os.path.join(localapp, "Vivaldi", "User Data")],
        "chromium": [os.path.join(localapp, "Chromium", "User Data")],
    }
    out: list[str] = []
    for base in bases.get(browser, []):
        # Opera keeps the profile at the base; Chrome-likes use Default/ under User Data.
        for sub in ("", "Default", "Profile 1"):
            root = os.path.join(base, sub) if sub else base
            out.append(os.path.join(root, "Network", "Cookies"))
            out.append(os.path.join(root, "Cookies"))
    return [p for p in out if os.path.exists(p)]


def _read_one(bc3, browser: str) -> Optional[str]:
    """Try a single browser; return a cookie header with a live FB session, or None."""
    loader = getattr(bc3, browser, None)
    if loader is None:
        return None
    cookie_files = _candidate_cookie_files(browser) or [None]
    for cf in cookie_files:
        try:
            cj = loader(cookie_file=cf, domain_name="facebook.com") if cf else loader(domain_name="facebook.com")
        except TypeError:
            cj = loader(domain_name="facebook.com")  # older signature w/o cookie_file
        except Exception as e:  # noqa: BLE001 — locked DB, ABE-encrypted cookies, no profile…
            global _last_error
            _last_error = f"{browser}: {type(e).__name__}: {e}"
            continue
        pairs = {c.name: c.value for c in cj if "facebook" in (c.domain or "")}
        if pairs.get("c_user") and pairs.get("xs"):
            return "; ".join(f"{k}={v}" for k, v in pairs.items() if v)
    return None


def _read_browser_cookies() -> Optional[str]:
    """Read facebook.com cookies from the local browser. Blocking — call in a thread."""
    global _last_error
    _last_error = ""
    if not bool(getattr(settings, "SCRAPER_USE_BROWSER_COOKIES", True)):
        _last_error = "browser auto-read disabled (SCRAPER_USE_BROWSER_COOKIES=false)"
        return None
    try:
        import browser_cookie3 as bc3
    except ImportError:
        _last_error = "browser-cookie3 not installed"
        logger.warning("browser-cookie3 not installed — `pip install browser-cookie3`.")
        return None

    browser = (getattr(settings, "SCRAPER_BROWSER", "auto") or "auto").lower()
    order = _BROWSER_ORDER if browser == "auto" else [browser]
    for b in order:
        cookie = _read_one(bc3, b)
        if cookie:
            logger.info("Read facebook.com session from %s.", b)
            return cookie

    if not _last_error:
        _last_error = "no logged-in facebook.com session found in any browser (no c_user/xs)"
    logger.info("Browser cookie read failed: %s", _last_error)
    return None


# ─── token bootstrap ───────────────────────────────────────────────────────

_DTSG_PATTERNS = [
    r'\["DTSGInitialData",\[\],\{"token":"([^"]+)"',
    r'DTSGInitialData",\[\],\{"token":"([^"]+)"',
    r'"DTSGInitData",\[\],\{"token":"([^"]+)"',
    r'"dtsg":\s*\{"token":"([^"]+)"',
    r'name="fb_dtsg"\s+value="([^"]+)"',
    r'"async_get_token":"([^"]+)"',
]
_LSD_PATTERNS = [
    r'\["LSD",\[\],\{"token":"([^"]+)"\}',
    r'"lsd":\s*\{"token":"([^"]+)"',
    r'name="lsd"\s+value="([^"]+)"',
]
_UID_PATTERNS = [r'"USER_ID":"(\d+)"', r'"actorID":"(\d+)"', r'"userID":"(\d+)"']


def _first_match(patterns: list[str], html: str) -> str:
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)
    return ""


_BOOTSTRAP_URLS = [
    "https://www.facebook.com/ads/library/",
    "https://www.facebook.com/",
    "https://www.facebook.com/business/",
]


async def _bootstrap_tokens(cookie: str) -> tuple[str, str, str]:
    """Fetch a logged-in FB page with the cookie and extract fb_dtsg / lsd / user_id.

    Tries several pages (the home page reliably carries DTSGInitialData) and logs
    what it found, so a 'no tokens' result is debuggable.
    """
    headers = {
        "User-Agent": getattr(settings, "SCRAPER_USER_AGENT", "") or _UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,fr;q=0.8,ar;q=0.7",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cookie": cookie,
    }
    proxy = getattr(settings, "SCRAPER_PROXY", "") or None
    try:
        async with httpx.AsyncClient(timeout=25, proxy=proxy, follow_redirects=True, headers=headers) as client:
            for url in _BOOTSTRAP_URLS:
                try:
                    r = await client.get(url)
                except httpx.HTTPError as e:
                    logger.warning("Token bootstrap GET %s failed: %s", url, e)
                    continue
                html = r.text
                dtsg = _first_match(_DTSG_PATTERNS, html)
                lsd = _first_match(_LSD_PATTERNS, html)
                uid = _first_match(_UID_PATTERNS, html)
                logged_in = '"USER_ID":"0"' not in html and len(html) > 5000
                logger.info(
                    "Token bootstrap %s: status=%s len=%d logged_in=%s dtsg=%s lsd=%s uid=%s",
                    url, r.status_code, len(html), logged_in, bool(dtsg), bool(lsd), bool(uid),
                )
                if dtsg or lsd:
                    return dtsg, lsd, uid
    except httpx.HTTPError as e:
        logger.warning("Token bootstrap client error: %s", e)
    return "", "", ""


# ─── disk cache ────────────────────────────────────────────────────────────

def _load_disk() -> Optional[FBSession]:
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        valid = {k: data[k] for k in FBSession.__dataclass_fields__ if k in data}
        return FBSession(**valid)
    except (OSError, ValueError, TypeError):
        return None


def _save_disk(sess: FBSession) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(asdict(sess), f)
    except OSError as e:
        logger.warning("Could not write session cache: %s", e)


# ─── public API ────────────────────────────────────────────────────────────

async def get_session(force: bool = False) -> Optional[FBSession]:
    """Resolve a usable Facebook session, or None if we can't get one."""
    global _cache

    if _cache and _cache.fresh() and not force:
        return _cache

    uid = ""

    # 1) manual env override
    env_cookie = (getattr(settings, "META_FB_COOKIE", "") or "").strip()
    if "c_user=" in env_cookie and "xs=" in env_cookie:
        cookie, source = env_cookie, "env"
        dtsg = (getattr(settings, "META_FB_DTSG", "") or "").strip()
        lsd = (getattr(settings, "META_FB_LSD", "") or "").strip()
    else:
        # 2) live browser session
        cookie = await asyncio.to_thread(_read_browser_cookies)
        source, dtsg, lsd = "browser", "", ""

    # 3) disk cache fallback (e.g., browser closed / locked right now)
    if not cookie:
        disk = _load_disk()
        if disk and disk.cookie:
            cookie, source = disk.cookie, "disk"
            dtsg, lsd, uid = disk.fb_dtsg, disk.lsd, disk.user_id
        else:
            _cache = None
            return None

    if not dtsg:
        dtsg, lsd2, uid2 = await _bootstrap_tokens(cookie)
        lsd, uid = (lsd or lsd2), (uid2 or uid)

    sess = FBSession(cookie=cookie, fb_dtsg=dtsg, lsd=lsd, user_id=uid, source=source, ts=time.time())
    _cache = sess
    _save_disk(sess)
    logger.info("Resolved Facebook session via %s (fb_dtsg=%s).", source, "yes" if dtsg else "no")
    return sess


def _normalize_cookie(raw: str) -> str:
    """Accept a raw cookie value, a 'Cookie: ...' header, or a 'Copy as cURL' blob."""
    raw = (raw or "").strip()
    low = raw.lower()
    idx = low.find("cookie:")
    if idx != -1:
        # Chromium 'Copy as cURL' wraps the whole header in quotes: -H 'cookie: ...'
        # so the enclosing quote sits BEFORE "cookie:". Detect it to know where to stop.
        j = idx - 1
        while j >= 0 and raw[j] == " ":
            j -= 1
        enclosing = raw[j] if j >= 0 and raw[j] in "'\"" else None

        rest = raw[idx + len("cookie:"):].lstrip()
        if rest[:1] in ("'", '"'):                 # cookie:"..."
            quote = rest[0]
            rest = rest[1:]
            end = rest.find(quote)
        elif enclosing:                            # '...cookie: ...'
            end = rest.find(enclosing)
        else:                                      # bare "Cookie: ..." header line
            rest = rest.splitlines()[0]
            end = -1
        raw = rest[:end] if end != -1 else rest
    return raw.strip().strip(";").strip()


async def set_manual_cookie(cookie: str) -> Optional[FBSession]:
    """Save a pasted facebook.com Cookie header: validate, bootstrap tokens, persist.

    Accepts a raw cookie, a 'Cookie:' header, or a 'Copy as cURL' paste.
    Survives restarts (cached to disk), so it's a paste-once flow — no .env edit.
    """
    global _cache, _last_error
    cookie = _normalize_cookie(cookie)
    if "c_user=" not in cookie or "xs=" not in cookie:
        _last_error = "pasted cookie is missing c_user/xs — copy the full Cookie header"
        return None
    dtsg, lsd, uid = await _bootstrap_tokens(cookie)
    sess = FBSession(cookie=cookie, fb_dtsg=dtsg, lsd=lsd, user_id=uid, source="manual", ts=time.time())
    _cache = sess
    _save_disk(sess)
    _last_error = ""
    logger.info("Manual Facebook cookie saved (fb_dtsg=%s).", "yes" if dtsg else "no")
    return sess


async def session_available() -> bool:
    return (await get_session()) is not None


def invalidate() -> None:
    """Drop the cached session so the next get_session() re-resolves from scratch."""
    global _cache
    _cache = None
    try:
        os.remove(CACHE_FILE)
    except OSError:
        pass


def describe_source() -> dict:
    """Lightweight, non-blocking snapshot for the status endpoint."""
    if _cache:
        return {"source": _cache.source, "has_tokens": bool(_cache.fb_dtsg),
                "user_id": _cache.user_id, "error": ""}
    return {"source": None, "has_tokens": False, "user_id": "", "error": _last_error}
