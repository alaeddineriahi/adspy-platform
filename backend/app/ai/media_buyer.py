"""
Media-buyer co-pilot — a conversational assistant that helps turn the winning
products/ads found in AdSpy into profitable ad campaigns.

v1 is ADVISORY: it streams expert media-buying guidance (budgets, audiences,
structure, testing, KPIs, scale/kill rules) grounded in the user's spy data.

FUTURE (wire Meta later): the co-pilot is intentionally split from execution.
When we add live Meta Marketing API control, an executor module
(app/mediabuyer/meta_executor.py) will consume a structured CampaignPlan and
create real campaigns/ad sets/ads. Keep that seam clean:
  • conversation + planning live here (provider-agnostic, via stream_llm),
  • execution/auth (ad account, tokens, create calls) lives separately,
  • the bridge is a structured plan object, not free text.
See settings.META_ACCESS_TOKEN / META_AD_ACCOUNT_ID for the eventual auth seam.
"""

from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator, Optional

from app.ai.script_generator import stream_llm
from app.core.elasticsearch import get_es_client

_PLAYBOOK_PATH = Path(__file__).parent / "knowledge" / "media_buying_playbook.md"


@lru_cache(maxsize=1)
def load_playbook() -> str:
    """Load the senior media-buying knowledge base (the co-pilot's 'skill').

    Injected as reference knowledge so advice is grounded in real tactics/
    benchmarks instead of the base model's generic marketing knowledge. Edit the
    markdown file to grow the skill; it's cached, so a process restart picks up changes.
    """
    try:
        return _PLAYBOOK_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


MEDIA_BUYER_SYSTEM = """You are a SENIOR direct-response media buyer with 8+ years and 8-figures of ad \
spend managed across the MENA region (Tunisia, Morocco, Algeria, Egypt, Saudi Arabia, UAE and the \
Gulf). You are embedded inside AdSpy as the user's personal media buyer. Most users are BEGINNERS \
running e-commerce / COD (cash-on-delivery) stores. Treat them like a smart mentee, not a client to \
impress.

# Your personality — honest senior mentor, NOT a yes-man
- NO flattery, NO sycophancy. Never open with "Great question", "Excellent", "You're on the right \
track", or empty praise. Lead with the answer.
- Tell the truth even when it's not what they want to hear. If their budget is too low, their idea is \
weak, their product is saturated, or their plan will burn money — say so plainly, then give the better \
move. You are doing them a disservice if you let them waste money to feel good.
- Have opinions. Make a clear recommendation ("do X, not Y, because Z"), don't list every option and \
shrug. When you make an assumption, state it in one line and move on.
- Be direct and concise. Respect their time and their money like it's your own.

# Beginner-first
- Assume low knowledge unless they show otherwise. The FIRST time you use a term (CBO, ABO, ROAS, CPA, \
CPM, hook rate, learning phase, Advantage+), add a 3-6 word plain-language gloss in parentheses.
- Give step-by-step, do-this-next instructions, not theory. One clear path beats five options.
- Set realistic expectations: most beginners' first 1-3 products lose money — that's tuition, not \
failure. Winning is about testing fast and cutting losers, not one perfect campaign.
- Don't dump everything at once. Give the next 1-2 concrete actions, then offer to go deeper.

# Tailor EVERYTHING to their setup (budget, country, creatives, experience)
- Always spend/plan WITHIN their stated budget and in their LOCAL currency. Never propose a structure \
their budget can't feed. Rough floor: an ad set needs ~2-3× the product's target CPA per day to exit \
the learning phase, so if their daily budget is small, run FEWER ad sets (often just ONE broad ad set), \
not many.
- Match the plan to how many creatives they actually have. You can't run a 3×3 test with 1 creative. \
If they have too few, tell them the minimum to start and how to get more cheaply (UGC, simple \
image/carousel, repurpose the winning ad's angle).
- Use their country's realities: COD confirmation/delivery rates, typical CPMs, buying behavior, best \
platform (Meta vs TikTok) for that market, Arabic vs French vs darija creative.

# Craft expertise
Campaign structure (CBO/ABO, Advantage+ Shopping), broad vs interest vs lookalike audiences, creative \
testing frameworks, KPI targets and DIAGNOSIS (CPM, CTR, CPC, hook rate, ATC, CPA/CPP, ROAS — what to \
do when each is off), learning phase, creative fatigue, scale & kill rules, budget pacing.

# Format
- Reply in the user's language (Arabic / French / English / darija) matching their message.
- Short sections and bullets with concrete numbers. A tight plan beats an essay.
- When they ask for a plan, cover only what fits their budget: objective, budget split (test → scale), \
structure, audiences, placements, creative/testing plan, KPI targets, scale/kill rules. End with the \
single most important next action.
- Ask a clarifying question ONLY if you truly can't help without it (and their setup profile below \
doesn't already answer it).

Constraint: you can't launch or edit ads directly yet — you produce plans the user runs in Meta/TikTok \
Ads Manager themselves. Never claim you launched or changed a live campaign."""


_CURRENCY_BY_COUNTRY = {
    "TN": "TND", "MA": "MAD", "DZ": "DZD", "EG": "EGP",
    "SA": "SAR", "AE": "AED", "KW": "KWD", "QA": "QAR",
    "US": "USD", "CA": "CAD", "GB": "GBP", "AU": "AUD", "FR": "EUR",
    "Tunisia": "TND", "Morocco": "MAD", "Algeria": "DZD", "Egypt": "EGP",
    "Saudi Arabia": "SAR", "UAE": "AED", "Kuwait": "KWD", "Qatar": "QAR",
}

_EXPERIENCE_LABELS = {
    "none": "complete beginner — has NEVER run a paid ad",
    "beginner": "beginner — has run a few campaigns, still learning",
    "intermediate": "intermediate — comfortable with Ads Manager basics",
}


def build_profile_context(profile: Optional[dict]) -> str:
    """Format the user's setup into a context block so advice is tailored to their means."""
    if not profile:
        return ""
    country = (profile.get("country") or "").strip()
    currency = (profile.get("currency") or _CURRENCY_BY_COUNTRY.get(country) or "").strip()
    budget = profile.get("budget")
    creatives = profile.get("creatives_count")
    ctypes = profile.get("creative_types") or []
    exp = _EXPERIENCE_LABELS.get(profile.get("experience") or "", profile.get("experience") or "")
    platform = (profile.get("platform") or "").strip()
    product = (profile.get("product") or "").strip()

    rows = []
    if country:
        rows.append(f"- Market / country: {country}" + (f" (spend & advise in {currency})" if currency else ""))
    if budget:
        rows.append(f"- Daily budget they can afford: {budget} {currency}".rstrip())
    if creatives is not None and str(creatives) != "":
        rows.append(f"- Creatives ready to run: {creatives}")
    if ctypes:
        rows.append(f"- Creative types they have: {', '.join(ctypes)}")
    if exp:
        rows.append(f"- Experience level: {exp}")
    if platform:
        rows.append(f"- Platform: {platform}")
    if product:
        rows.append(f"- Product / niche: {product}")
    brand = (profile.get("brand_summary") or "").strip()
    if brand:
        rows.append(f"- THEIR BRAND (from analyzing their website — treat as ground truth):\n{brand}")
    if not rows:
        return ""
    return (
        "THE USER'S SETUP (tailor every recommendation to this — budget, market, "
        "creatives and experience level):\n" + "\n".join(rows)
    )


async def build_ad_context(ad_id: Optional[str]) -> str:
    """Fetch a spied ad and format it as grounding context for the co-pilot."""
    if not ad_id:
        return ""
    es = get_es_client()
    try:
        doc = await es.get(index="ads", id=ad_id)
        ad = doc["_source"]
    except Exception:
        return ""
    finally:
        await es.close()

    copy = (ad.get("copy_text") or "").strip()
    if len(copy) > 800:
        copy = copy[:800] + "…"
    lines = [
        "The user is asking about this WINNING AD they found in AdSpy:",
        f"- Advertiser: {ad.get('advertiser_name', 'Unknown')}",
        f"- Country: {ad.get('country', '?')}  |  Platform: {ad.get('platform', 'meta')}  |  Format: {ad.get('ad_format', '?')}",
        f"- Days running: {ad.get('days_running', '?')}  |  Variants (scaling): {ad.get('variant_count', '?')}  |  Money score: {ad.get('performance_score', '?')}/100",
        f"- CTA: {ad.get('cta_text') or '—'}",
        f"- Landing page: {ad.get('landing_page') or '—'}",
        f"- Ad copy: {copy or '—'}",
        "",
        "Use this as the product/offer to build the media plan around.",
    ]
    return "\n".join(lines)


async def stream_chat(
    messages: list[dict],
    ad_id: Optional[str] = None,
    profile: Optional[dict] = None,
) -> AsyncIterator[str]:
    """Stream the media-buyer's reply, grounded in the playbook and tailored to the
    user's setup (and optionally a spied ad)."""
    system = MEDIA_BUYER_SYSTEM
    playbook = load_playbook()
    if playbook:
        system = f"{system}\n\n===== REFERENCE KNOWLEDGE (apply, don't recite) =====\n{playbook}"
    # Most-specific context last so it dominates: user's setup, then the spied ad.
    for block in (build_profile_context(profile), await build_ad_context(ad_id)):
        if block:
            system = f"{system}\n\n---\n{block}"
    async for delta in stream_llm(system, messages):
        yield delta
