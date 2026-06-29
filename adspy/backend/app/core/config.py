"""
App configuration — loads from .env file.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "AdSpy"
    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://adspy:adspy@localhost:5432/adspy"

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Elasticsearch ---
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # --- Auth (Clerk) ---
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""

    # --- AI Provider ---
    # "groq" (free, dev) or "anthropic" (paid, production)
    AI_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""          # Free: https://console.groq.com
    ANTHROPIC_API_KEY: str = ""     # Paid: for production

    # --- Scraping (Meta Ad Library API — free) ---
    # Get token: https://developers.facebook.com → your app → Graph API Explorer
    # Required permission: ads_read
    META_ACCESS_TOKEN: str = ""

    # --- Storage (Cloudflare R2) ---
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET_NAME: str = "adspy-media"
    R2_ENDPOINT: str = ""

    # --- Payments (Tunisia) ---
    # Konnect (primary) — https://konnect.network
    KONNECT_API_KEY: str = ""
    KONNECT_WALLET_ID: str = ""
    KONNECT_SANDBOX: bool = True    # True for dev, False for production

    # Flouci (secondary) — https://flouci.com
    FLOUCI_APP_TOKEN: str = ""
    FLOUCI_APP_SECRET: str = ""

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
