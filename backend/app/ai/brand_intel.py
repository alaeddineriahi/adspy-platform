"""
Website Intel — paste a store URL, get a structured brand/product breakdown.

Fetches the page server-side (with an SSRF guard, since we're fetching
user-supplied URLs), extracts the marketing-relevant text, and has the LLM
produce a structured brand profile: what they sell, audience, offers, USPs,
ad angles, and AdSpy search terms to find similar winning ads.
"""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

import httpx

from app.ai.script_generator import _call_llm

logger = logging.getLogger("adspy.brand_intel")

_MAX_BYTES = 2_000_000  # never read more than ~2MB of HTML
_MAX_TEXT = 12_000      # cap what we hand to the LLM

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)


class FetchError(Exception):
    """User-facing fetch problem (bad URL, unreachable, blocked)."""


def _assert_public_host(url: str) -> str:
    """SSRF guard: only plain http(s) to hosts that resolve to PUBLIC IPs."""
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in ("http", "https"):
        raise FetchError("Only http(s) URLs are supported.")
    host = parsed.hostname or ""
    if not host or "." not in host:
        raise FetchError("That doesn't look like a valid website address.")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise FetchError(f"Couldn't resolve {host} — check the address.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise FetchError("That address isn't reachable from here.")
    return parsed.geturl()


async def _fetch_html(url: str) -> tuple[str, str]:
    """Returns (final_url, html). Raises FetchError with a friendly message."""
    safe_url = _assert_public_host(url)
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": _UA, "Accept-Language": "fr,ar;q=0.9,en;q=0.8"},
        ) as client:
            resp = await client.get(safe_url)
    except httpx.HTTPError as e:
        raise FetchError(f"Couldn't reach the site ({type(e).__name__}).")
    if resp.status_code >= 400:
        raise FetchError(f"The site answered HTTP {resp.status_code}.")
    # Redirects may land elsewhere — re-check the final host too.
    _assert_public_host(str(resp.url))
    ctype = resp.headers.get("content-type", "")
    if "html" not in ctype and "text" not in ctype:
        raise FetchError("That URL isn't a web page.")
    return str(resp.url), resp.text[:_MAX_BYTES]


def _extract_content(html: str) -> str:
    """Marketing-relevant text only: title, metas, headings, CTAs, body."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    parts: list[str] = []
    if soup.title and soup.title.string:
        parts.append(f"TITLE: {soup.title.string.strip()}")
    for name, key in (("description", "name"), ("og:title", "property"),
                      ("og:description", "property"), ("og:site_name", "property")):
        tag = soup.find("meta", attrs={key: name})
        if tag and tag.get("content"):
            parts.append(f"META {name}: {tag['content'].strip()}")

    for h in soup.find_all(["h1", "h2", "h3"], limit=25):
        text = h.get_text(" ", strip=True)
        if text:
            parts.append(f"HEADING: {text}")

    for b in soup.find_all(["button", "a"], limit=200):
        text = b.get_text(" ", strip=True)
        if text and 2 < len(text) < 40 and re.search(
            r"buy|shop|order|cart|commander|acheter|panier|اشتر|اطلب|شراء", text, re.I
        ):
            parts.append(f"CTA: {text}")

    body = soup.get_text(" ", strip=True)
    body = re.sub(r"\s{2,}", " ", body)
    parts.append(f"PAGE TEXT: {body}")

    return "\n".join(parts)[:_MAX_TEXT]


_SYSTEM = """You are a senior MENA e-commerce strategist. You are given the raw text
of a brand's website. Produce a sharp, factual brand intelligence brief.

Rules:
- Base EVERYTHING on the page text. If something isn't stated, infer cautiously
  and mark it as an inference; never invent specifics like prices.
- Keep the language of quotes/product names as found (Arabic/French stays as-is);
  write your analysis in English.
- Return STRICT JSON with exactly these keys:
{
  "brand_name": str,
  "one_liner": str,                       // what this brand is, in one sentence
  "niche": str,                           // e.g. "skincare", "modest fashion"
  "products": [{"name": str, "price": str|null}],   // up to 6, price only if literally on the page
  "target_audience": str,                 // who buys this, be specific
  "price_positioning": str,               // budget / mid / premium + why
  "offers_and_hooks": [str],              // promos, guarantees, delivery offers found
  "usp": [str],                           // up to 4 differentiators
  "tone_of_voice": str,
  "ad_angles": [str],                     // 4-6 concrete angles for THIS brand's ads
  "spy_search_terms": [str],              // 3-5 short terms to find similar winning ads (mix FR/AR if relevant)
  "confidence": "high"|"medium"|"low"     // how much signal the page actually gave
}"""


async def analyze_website(url: str) -> dict:
    final_url, html = await _fetch_html(url)
    content = _extract_content(html)
    if len(content) < 200:
        raise FetchError(
            "The page returned almost no readable text (probably a fully "
            "JavaScript-rendered site). Try a specific product page instead."
        )
    result = await _call_llm(_SYSTEM, f"WEBSITE: {final_url}\n\n{content}")
    import json

    data = json.loads(result)
    data["source_url"] = final_url
    return data
