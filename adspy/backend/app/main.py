from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import ads, brands, ai, users
from app.core.config import settings

app = FastAPI(
    title="AdSpy API",
    description="Ad intelligence platform API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ads.router, prefix="/api/ads", tags=["ads"])
app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
app.include_router(users.router, prefix="/api/user", tags=["users"])


@app.get("/health")
async def health():
    return {"status": "ok"}
