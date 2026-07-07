"""
Live web search for the Brand Hunter's open-web discovery source.

Provider-agnostic: Serper (Google), Tavily (AI-native), or Brave. Returns raw
result text (titles + snippets) for the caller to mine. Fail-soft — any error
or a missing key returns [], so the hunter's other sources keep working.

This exists so brand discovery can be grounded in TODAY's web, not an LLM's
training data: we fetch fresh results, then the LLM extracts names only from
that fetched text.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("adspy.web_research")


def search_enabled() -> bool:
    return bool((getattr(settings, "SEARCH_API_KEY", "") or "").strip())


def _provider() -> str:
    return (getattr(settings, "SEARCH_API_PROVIDER", "serper") or "serper").strip().lower()


async def _serper(query: str, key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": 10},
        )
        r.raise_for_status()
        data = r.json()
    out = []
    for item in data.get("organic", []):
        out.append(f"{item.get('title', '')} — {item.get('snippet', '')}".strip(" —"))
    return out


async def _tavily(query: str, key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": 10, "search_depth": "basic"},
        )
        r.raise_for_status()
        data = r.json()
    return [f"{it.get('title', '')} — {it.get('content', '')}".strip(" —")
            for it in data.get("results", [])]


async def _brave(query: str, key: str) -> list[str]:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
            params={"q": query, "count": 10},
        )
        r.raise_for_status()
        data = r.json()
    return [f"{it.get('title', '')} — {it.get('description', '')}".strip(" —")
            for it in data.get("web", {}).get("results", [])]


async def search_web(query: str) -> list[str]:
    """Live search results (title — snippet strings). [] on any failure."""
    key = (getattr(settings, "SEARCH_API_KEY", "") or "").strip()
    if not key:
        return []
    provider = _provider()
    fn = {"serper": _serper, "tavily": _tavily, "brave": _brave}.get(provider)
    if not fn:
        logger.warning("Unknown SEARCH_API_PROVIDER %r — expected serper|tavily|brave.", provider)
        return []
    try:
        return await fn(query, key)
    except Exception as e:  # noqa: BLE001 — research is additive, never fatal
        logger.warning("web search (%s) failed for %r: %s", provider, query, e)
        return []
