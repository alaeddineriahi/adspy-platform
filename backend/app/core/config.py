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
    DEBUG_SQL: bool = False   # set true to echo every SQL statement (verbose)

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

    # --- Meta Ad Library (official Graph API) ---
    META_ACCESS_TOKEN: str = ""
    META_API_VERSION: str = "v21.0"
    # Ad account for the (future) live media-buyer execution seam, e.g. act_1234567890.
    # When this + META_ACCESS_TOKEN are set, /api/mediabuyer/capabilities reports
    # meta_execution=true and the executor can create real campaigns.
    META_AD_ACCOUNT_ID: str = ""

    # --- Scraping (legacy / unused) ---
    BRIGHTDATA_API_KEY: str = ""
    BRIGHTDATA_CUSTOMER_ID: str = ""

    # --- Self-serve Ad Library ingestion (scraper) ---
    # Logged-in facebook.com session so the scraper can read the full Ad Library.
    META_FB_COOKIE: str = ""        # OPTIONAL manual override (must include c_user= and xs=)
    META_FB_DTSG: str = ""          # fb_dtsg token from the same session
    META_FB_LSD: str = ""           # lsd token from the same session (optional)
    SCRAPER_USER_AGENT: str = ""    # override the default desktop UA
    SCRAPER_PROXY: str = ""         # optional http(s) proxy, e.g. http://user:pass@host:port

    # Auto-read the facebook.com session from your browser (no manual cookie).
    SCRAPER_USE_BROWSER_COOKIES: bool = True
    SCRAPER_BROWSER: str = "auto"   # auto | chrome | edge | firefox | brave | opera | opera_gx
    SCRAPER_COOKIE_FILE: str = ""   # explicit path to the browser Cookies DB (optional override)

    # Autonomous schedule
    INGEST_SCHEDULE_ENABLED: bool = False
    INGEST_INTERVAL_HOURS: float = 12

    # Sweep scope (comma-separated strings in .env, or use defaults)
    INGEST_COUNTRIES: str = ""      # e.g. "TN,MA,EG,SA,AE"
    INGEST_SEARCH_TERMS: str = ""   # e.g. "livraison gratuite,promo,تخفيضات"

    # Best-performing thresholds
    INGEST_MIN_DAYS_RUNNING: int = 7
    INGEST_MIN_VARIANTS: int = 3
    INGEST_MAX_PER_COUNTRY: int = 40

    # --- Storage (Cloudflare R2) ---
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET: str = "adspy-media"
    R2_BUCKET_NAME: str = "adspy-media"
    R2_ENDPOINT: str = ""
    R2_PUBLIC_URL: str = ""   # public dev URL, e.g. https://pub-xxxx.r2.dev

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
