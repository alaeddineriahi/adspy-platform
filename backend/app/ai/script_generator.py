"""
AI Script/Copy/Analysis generator.

DEV MODE:  Uses Groq free tier (Llama 3.3 70B) — no cost.
PROD MODE: Set AI_PROVIDER=anthropic in .env to switch to Claude API.

The swap is ONE config change. Both providers use the same prompt templates
and return the same JSON structure.
"""

import json
import httpx
from typing import AsyncIterator, Optional
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
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    # json_object mode 400s unless the prompt literally contains "JSON"
    # (OpenAI-compat rule) — only request it when it's allowed, so a prompt
    # edit can never silently break every AI feature.
    if "json" in (system_prompt + user_prompt).lower():
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        if resp.status_code == 400 and "response_format" in payload:
            # belt & braces: retry once without forced-JSON mode
            payload.pop("response_format")
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
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


# ─── Streaming (for the conversational media-buyer co-pilot) ────────

async def stream_llm(
    system_prompt: str,
    messages: list[dict],
    temperature: float = 0.6,
    max_tokens: int = 1600,
) -> AsyncIterator[str]:
    """Stream a chat completion token-by-token, routed to Groq or Claude.

    `messages` is a list of {"role": "user"|"assistant", "content": str},
    oldest first. Yields text deltas as they arrive.
    """
    provider = getattr(settings, "AI_PROVIDER", "groq")
    if provider == "anthropic":
        async for delta in _stream_claude(system_prompt, messages, temperature, max_tokens):
            yield delta
    else:
        async for delta in _stream_groq(system_prompt, messages, temperature, max_tokens):
            yield delta


async def _stream_groq(system_prompt, messages, temperature, max_tokens) -> AsyncIterator[str]:
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system_prompt}, *messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        async with client.stream(
            "POST",
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "ignore")
                raise RuntimeError(f"Groq {resp.status_code}: {body[:300]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    delta = json.loads(data)["choices"][0]["delta"].get("content")
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                if delta:
                    yield delta


async def _stream_claude(system_prompt, messages, temperature, max_tokens) -> AsyncIterator[str]:
    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=90) as client:
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = (await resp.aread()).decode("utf-8", "ignore")
                raise RuntimeError(f"Claude {resp.status_code}: {body[:300]}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "content_block_delta":
                    text = event.get("delta", {}).get("text")
                    if text:
                        yield text


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

VIDEO_SCRIPT_SYSTEM = """You are a world-class direct-response video ad scriptwriter for the MENA market,
fluent in Arabic, French, and English. You write SHORT-FORM video scripts (Meta Reels / TikTok / Stories)
that are engineered to convert, not generic marketing fluff.

Hard rules:
- The HOOK must stop the scroll in the first 3 seconds (pattern interrupt, bold claim, or visceral problem).
- Every scene must EARN the next second of attention. No filler. Spoken lines must be punchy and natural.
- Use proven direct-response structure: HOOK -> PROBLEM/AGITATE -> SOLUTION -> PROOF -> OFFER -> CTA.
- Write the voiceover in the requested language; keep on_screen_text short and skimmable.
- Be specific to the product and audience given. Reference concrete benefits, objections, and outcomes.
- Total spoken length must fit the requested duration.

ALWAYS respond in valid JSON with EXACTLY this structure:
{
  "concept": "the one-line big idea / angle of this ad",
  "hooks": [
    {"type": "emotional", "text": "scroll-stopping hook line"},
    {"type": "curiosity", "text": "scroll-stopping hook line"},
    {"type": "contrarian", "text": "scroll-stopping hook line"}
  ],
  "scenes": [
    {
      "timestamp": "0:00-0:03",
      "beat": "Hook",
      "visual": "what is on screen / shot direction",
      "on_screen_text": "short caption overlay",
      "voiceover": "exact words spoken"
    }
  ],
  "cta": "final call to action line",
  "caption": "ready-to-post caption with 3-5 relevant hashtags",
  "music_vibe": "suggested music/sound style",
  "tips": ["short actionable production/optimization tip", "another tip"]
}

The "scenes" array MUST cover, in order, these beats: Hook, Problem, Solution, Proof, Offer, CTA
(merge or split only if it clearly improves conversion). Timestamps must add up to roughly the target duration."""

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


_LANG_NAMES = {"en": "English", "fr": "French", "ar": "Arabic"}


async def generate_video_script(
    product: str,
    audience: str,
    platform: str = "meta",
    language: str = "en",
    duration: int = 30,
    tone: str = "energetic direct-response",
) -> dict:
    """Generate a high-converting short-form video ad script from a product brief."""
    lang_name = _LANG_NAMES.get(language, language)
    user_prompt = f"""Write a high-converting short-form VIDEO AD SCRIPT.

Product/Service: {product}
Target audience: {audience}
Platform: {platform} ({'vertical 9:16 short-form video' if platform != 'meta' else 'Meta Reels/Stories, vertical 9:16'})
Spoken language for voiceover: {lang_name}
Target duration: {duration} seconds
Tone: {tone}

Engineer it to convert: a 3-second scroll-stopping hook, tight problem agitation,
a clear solution, concrete proof, an irresistible offer, and a strong CTA.
Give 3 distinct hook options and a full scene-by-scene breakdown."""

    result = await _call_llm(VIDEO_SCRIPT_SYSTEM, user_prompt)
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
