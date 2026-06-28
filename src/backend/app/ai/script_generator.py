"""
AI Script/Copy/Analysis generator.

DEV MODE:  Uses Groq free tier (Llama 3.3 70B) — no cost.
PROD MODE: Set AI_PROVIDER=anthropic in .env to switch to Claude API.

The swap is ONE config change. Both providers use the same prompt templates
and return the same JSON structure.
"""

import json
import httpx
from typing import Optional
from app.core.config import settings


# ─── Provider abstraction ───────────────────────────────────────────

async def _call_llm(system_prompt: str, user_prompt: str) -> str:
    """Route to Groq or Claude based on AI_PROVIDER env var."""
    provider = getattr(settings, "AI_PROVIDER", "groq")

    if provider == "anthropic":
        return await _call_claude(system_prompt, user_prompt)
    else:
        return await _call_groq(system_prompt, user_prompt)


async def _call_groq(system_prompt: str, user_prompt: str) -> str:
    """Groq free tier — Llama 3.3 70B. 30 RPM, 6K TPM free."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_claude(system_prompt: str, user_prompt: str) -> str:
    """Claude API — production quality. Swap by setting AI_PROVIDER=anthropic."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2048,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


# ─── System prompts ────────────────────────────────────────────────

SCRIPT_SYSTEM = """You are an expert MENA-region ad copywriter fluent in Arabic, French, and English.
You analyze winning ads and generate viral video scripts.

ALWAYS respond in valid JSON with this structure:
{
  "hooks": {
    "emotional": "hook text",
    "curiosity": "hook text",
    "contrarian": "hook text"
  },
  "script": {
    "hook": "opening line",
    "problem": "pain point section",
    "solution": "product positioning",
    "proof": "social proof / results",
    "cta": "call to action"
  },
  "language": "detected language of original ad",
  "target_audience": "inferred audience"
}"""

COPY_SYSTEM = """You are an expert ad copywriter for the MENA market.
Generate platform-specific ad copy variations.

ALWAYS respond in valid JSON with this structure:
{
  "variations": [
    {
      "headline": "ad headline",
      "primary_text": "main ad copy",
      "cta": "call to action text",
      "platform": "meta|tiktok",
      "tone": "description of tone used"
    }
  ],
  "tips": ["tip1", "tip2"]
}"""

ANALYZER_SYSTEM = """You are an ad creative analyst specializing in MENA markets.
Score ads on multiple dimensions.

ALWAYS respond in valid JSON with this structure:
{
  "scores": {
    "hook_strength": 0-100,
    "copy_clarity": 0-100,
    "cta_effectiveness": 0-100,
    "visual_appeal": 0-100,
    "audience_targeting": 0-100
  },
  "overall_score": 0-100,
  "strengths": ["strength1", "strength2"],
  "improvements": ["improvement1", "improvement2"],
  "rewrite_suggestion": "improved version of the ad copy"
}"""


# ─── Public API ────────────────────────────────────────────────────

async def generate_script(ad_copy: str, advertiser: str, platform: str) -> dict:
    """Analyze a winning ad and generate hook variations + full script."""
    user_prompt = f"""Analyze this winning ad and generate a video script:

Advertiser: {advertiser}
Platform: {platform}
Ad copy: {ad_copy}

Generate 3 hook variations (emotional, curiosity, contrarian) and a full
HOOK > PROBLEM > SOLUTION > PROOF > CTA script structure."""

    result = await _call_llm(SCRIPT_SYSTEM, user_prompt)
    return json.loads(result)


async def generate_copy(
    product: str,
    audience: str,
    platform: str = "meta",
    language: str = "en",
    num_variations: int = 3,
) -> dict:
    """Generate ad copy from a product brief."""
    user_prompt = f"""Generate {num_variations} ad copy variations:

Product/Service: {product}
Target audience: {audience}
Platform: {platform}
Language: {language}

Make each variation have a different angle/tone."""

    result = await _call_llm(COPY_SYSTEM, user_prompt)
    return json.loads(result)


async def analyze_creative(
    ad_copy: str,
    platform: str = "meta",
    ad_format: str = "image",
) -> dict:
    """Score an ad creative and suggest improvements."""
    user_prompt = f"""Analyze this ad creative:

Platform: {platform}
Format: {ad_format}
Ad copy: {ad_copy}

Score each dimension 0-100 and provide actionable improvements."""

    result = await _call_llm(ANALYZER_SYSTEM, user_prompt)
    return json.loads(result)
