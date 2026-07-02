"""
AI API routes — script generation, copy writing, creative analysis.

Each generation requires a signed-in user and spends 1 AI credit (402 when
the monthly allowance is exhausted) — see app/core/credits.py.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.ai.script_generator import (
    generate_script,
    generate_copy,
    generate_video_script,
    analyze_creative,
)
from app.core.auth import get_user_id
from app.core.credits import spend_credits
from app.core.elasticsearch import get_es_client

router = APIRouter()


class ScriptRequest(BaseModel):
    ad_id: str
    language: str = "en"
    product_context: str = ""


class VideoScriptRequest(BaseModel):
    product: str
    audience: str
    platform: str = "meta"
    language: str = "en"
    duration: int = 30
    tone: str = "energetic direct-response"


class CopyRequest(BaseModel):
    product: str
    audience: str
    platform: str = "meta"
    tone: str = "professional"
    language: str = "en"
    num_variations: int = 3


class AnalyzeRequest(BaseModel):
    ad_id: Optional[str] = None
    copy_text: Optional[str] = None
    platform: str = "meta"


@router.post("/generate-script")
async def api_generate_script(req: ScriptRequest, uid: str = Depends(get_user_id)):
    """Generate hooks + video script from a winning ad."""
    # Fetch the ad from Elasticsearch first — don't spend a credit on a 404.
    es = get_es_client()
    try:
        ad_data = await es.get(index="ads", id=req.ad_id)
        ad = ad_data["_source"]
    except Exception:
        raise HTTPException(status_code=404, detail="Ad not found")
    finally:
        await es.close()

    credits = await spend_credits(uid)

    result = await generate_script(
        ad_copy=ad.get("copy_text", ""),
        advertiser=ad.get("advertiser_name", ""),
        platform=ad.get("platform", "meta"),
    )

    return {**result, "credits": credits, "source_ad_id": req.ad_id}


@router.post("/generate-video-script")
async def api_generate_video_script(req: VideoScriptRequest, uid: str = Depends(get_user_id)):
    """Generate a high-converting short-form video ad script from a product brief."""
    credits = await spend_credits(uid)
    result = await generate_video_script(
        product=req.product,
        audience=req.audience,
        platform=req.platform,
        language=req.language,
        duration=req.duration,
        tone=req.tone,
    )
    return {**result, "credits": credits}


@router.post("/generate-copy")
async def api_generate_copy(req: CopyRequest, uid: str = Depends(get_user_id)):
    """Generate ad copy from product brief."""
    credits = await spend_credits(uid)
    result = await generate_copy(
        product=req.product,
        audience=req.audience,
        platform=req.platform,
        language=req.language,
        num_variations=req.num_variations,
    )
    return {**result, "credits": credits}


@router.post("/analyze")
async def api_analyze(req: AnalyzeRequest, uid: str = Depends(get_user_id)):
    """Analyze and score an ad creative."""
    copy_text = req.copy_text
    platform = req.platform
    advertiser = ""
    ad_format = "image"

    if req.ad_id:
        es = get_es_client()
        try:
            ad_data = await es.get(index="ads", id=req.ad_id)
            ad = ad_data["_source"]
            copy_text = ad.get("copy_text", "")
            platform = ad.get("platform", "meta")
            advertiser = ad.get("advertiser_name", "")
            ad_format = ad.get("ad_format", "image")
        except Exception:
            raise HTTPException(status_code=404, detail="Ad not found")
        finally:
            await es.close()

    if not copy_text:
        raise HTTPException(status_code=400, detail="No ad copy to analyze")

    credits = await spend_credits(uid)
    result = await analyze_creative(
        ad_copy=copy_text,
        platform=platform,
        ad_format=ad_format,
    )
    return {**result, "credits": credits}
