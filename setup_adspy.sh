#!/bin/bash
# AdSpy Platform - Project Scaffolding Script
# Run: chmod +x setup_adspy.sh && ./setup_adspy.sh
# Requires: Node.js 18+, Python 3.11+, Docker

set -e

echo "=== AdSpy Platform Setup ==="
echo ""

# Root
mkdir -p adspy && cd adspy

# ============================================================
# FRONTEND (Next.js 14)
# ============================================================
echo "[1/4] Creating Next.js frontend..."

npx create-next-app@14 frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-turbo

cd frontend

# Install dependencies
npm install @clerk/nextjs@^5 @tanstack/react-query@^5 axios lucide-react clsx tailwind-merge zustand date-fns

# Create directory structure
mkdir -p src/app/\(auth\)/sign-in/[[...sign-in]]
mkdir -p src/app/\(auth\)/sign-up/[[...sign-up]]
mkdir -p src/app/\(dashboard\)/search
mkdir -p src/app/\(dashboard\)/ad/[id]
mkdir -p src/app/\(dashboard\)/brands
mkdir -p src/app/\(dashboard\)/brands/[id]
mkdir -p src/app/\(dashboard\)/ai
mkdir -p src/app/\(dashboard\)/saved
mkdir -p src/app/\(dashboard\)/settings
mkdir -p src/components/ads
mkdir -p src/components/brands
mkdir -p src/components/ai
mkdir -p src/components/ui
mkdir -p src/lib
mkdir -p src/hooks
mkdir -p src/types

# --- .env.local ---
cat > .env.local << 'ENVEOF'
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your_key_here
CLERK_SECRET_KEY=sk_test_your_key_here
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_API_URL=http://localhost:8000
ENVEOF

# --- Middleware (Clerk auth) ---
cat > src/middleware.ts << 'EOF'
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isPublicRoute = createRouteMatcher([
  "/",
  "/sign-in(.*)",
  "/sign-up(.*)",
  "/api/webhooks(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
    await auth.protect();
  }
});

export const config = {
  matcher: ["/((?!.*\\..*|_next).*)", "/", "/(api|trpc)(.*)"],
};
EOF

# --- Root layout ---
cat > src/app/layout.tsx << 'EOF'
import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AdSpy - Ad Intelligence Platform",
  description: "Spy, swipe, and create winning ads. The ultimate ad library for MENA marketers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={inter.className}>{children}</body>
      </html>
    </ClerkProvider>
  );
}
EOF

# --- Landing page ---
cat > src/app/page.tsx << 'EOF'
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 text-white">
      <nav className="flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold">AdSpy</h1>
        <div className="flex gap-4">
          <Link href="/sign-in" className="px-4 py-2 text-sm text-gray-300 hover:text-white">
            Log in
          </Link>
          <Link href="/sign-up" className="px-4 py-2 text-sm bg-blue-600 rounded-lg hover:bg-blue-500">
            Start free trial
          </Link>
        </div>
      </nav>
      <section className="max-w-4xl mx-auto text-center pt-32 px-6">
        <h2 className="text-5xl font-bold leading-tight mb-6">
          Stop wasting ad spend.<br />Start scaling profitably.
        </h2>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          Spy on competitor ads across Meta and TikTok. Generate winning scripts with AI.
          Built for MENA marketers.
        </p>
        <Link
          href="/sign-up"
          className="inline-block px-8 py-4 bg-blue-600 text-lg font-semibold rounded-xl hover:bg-blue-500 transition"
        >
          Try free for 7 days
        </Link>
        <p className="mt-4 text-sm text-gray-500">No credit card required</p>
      </section>
    </main>
  );
}
EOF

# --- Auth pages ---
cat > "src/app/(auth)/sign-in/[[...sign-in]]/page.tsx" << 'EOF'
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <SignIn />
    </div>
  );
}
EOF

cat > "src/app/(auth)/sign-up/[[...sign-up]]/page.tsx" << 'EOF'
import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <SignUp />
    </div>
  );
}
EOF

# --- Dashboard layout ---
cat > "src/app/(dashboard)/layout.tsx" << 'EOF'
import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { Search, Bookmark, Zap, Eye, Settings } from "lucide-react";

const navItems = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/brands", label: "Brand Spy", icon: Eye },
  { href: "/ai", label: "AI Tools", icon: Zap },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6">
          <h1 className="text-xl font-bold text-gray-900">AdSpy</h1>
        </div>
        <nav className="flex-1 px-3">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 rounded-lg hover:bg-gray-100 mb-1"
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-200">
          <UserButton afterSignOutUrl="/" />
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
EOF

# --- Search page ---
cat > "src/app/(dashboard)/search/page.tsx" << 'EOF'
"use client";

import { useState } from "react";
import { Search, Filter, SlidersHorizontal } from "lucide-react";

type Platform = "all" | "meta" | "tiktok";
type AdFormat = "all" | "image" | "video" | "carousel";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState<Platform>("all");
  const [format, setFormat] = useState<AdFormat>("all");
  const [country, setCountry] = useState("all");

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Search ads</h2>

      {/* Search bar */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by keyword, brand, or domain..."
          className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-8">
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value as Platform)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">All platforms</option>
          <option value="meta">Meta (FB + IG)</option>
          <option value="tiktok">TikTok</option>
        </select>

        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as AdFormat)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">All formats</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="carousel">Carousel</option>
        </select>

        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">All countries</option>
          <option value="TN">Tunisia</option>
          <option value="DZ">Algeria</option>
          <option value="MA">Morocco</option>
          <option value="EG">Egypt</option>
          <option value="SA">Saudi Arabia</option>
          <option value="AE">UAE</option>
        </select>

        <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">
          <SlidersHorizontal className="w-4 h-4" />
          More filters
        </button>
      </div>

      {/* Results placeholder */}
      <div className="text-center py-20 text-gray-400">
        <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p className="text-lg">Search for ads to get started</p>
        <p className="text-sm mt-2">Try &quot;e-commerce Tunisia&quot; or &quot;fashion UAE&quot;</p>
      </div>
    </div>
  );
}
EOF

# --- API client ---
cat > src/lib/api.ts << 'EOF'
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach Clerk token to requests
api.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    const { Clerk } = await import("@clerk/nextjs");
    // Token will be attached via Clerk's session
  }
  return config;
});

// API functions
export const searchAds = (params: {
  q?: string;
  platform?: string;
  format?: string;
  country?: string;
  page?: number;
  limit?: number;
}) => api.get("/api/ads/search", { params });

export const getAd = (id: string) => api.get(`/api/ads/${id}`);

export const searchBrands = (q: string) => api.get("/api/brands/search", { params: { q } });

export const getBrandAds = (id: string) => api.get(`/api/brands/${id}/ads`);

export const generateScript = (adId: string) =>
  api.post("/api/ai/generate-script", { ad_id: adId });

export const generateCopy = (data: { product: string; audience: string; platform: string }) =>
  api.post("/api/ai/generate-copy", data);

export const saveAd = (adId: string, board: string) =>
  api.post("/api/user/save", { ad_id: adId, board });

export const getSavedAds = () => api.get("/api/user/saved");
EOF

# --- Types ---
cat > src/types/index.ts << 'EOF'
export interface Ad {
  id: string;
  platform: "meta" | "tiktok" | "google";
  advertiser_name: string;
  advertiser_id: string;
  ad_id: string;
  country: string;
  language: string;
  ad_format: "image" | "video" | "carousel";
  copy_text: string;
  cta_text: string;
  landing_page: string;
  media_urls: string[];
  first_seen: string;
  last_seen: string;
  is_active: boolean;
  days_running: number;
}

export interface Brand {
  advertiser_id: string;
  advertiser_name: string;
  platform: string;
  total_ads: number;
  active_ads: number;
  countries: string[];
}

export interface AIGeneration {
  id: string;
  type: "script" | "copy" | "analysis";
  output: {
    hooks: string[];
    script?: string;
    copy?: string;
    score?: number;
    suggestions?: string[];
  };
  created_at: string;
}

export interface UserUsage {
  plan: "free" | "pro" | "agency";
  searches_today: number;
  searches_limit: number;
  credits_remaining: number;
  credits_limit: number;
}
EOF

# --- Ad card component ---
cat > src/components/ads/AdCard.tsx << 'EOF'
"use client";

import { Ad } from "@/types";
import { Bookmark, ExternalLink, Clock, Globe } from "lucide-react";
import Link from "next/link";

export function AdCard({ ad }: { ad: Ad }) {
  const platformColors = {
    meta: "bg-blue-100 text-blue-700",
    tiktok: "bg-gray-900 text-white",
    google: "bg-green-100 text-green-700",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition group">
      {/* Media preview */}
      <div className="aspect-video bg-gray-100 relative">
        {ad.media_urls[0] && (
          <img
            src={ad.media_urls[0]}
            alt={ad.advertiser_name}
            className="w-full h-full object-cover"
          />
        )}
        <span className={`absolute top-3 left-3 px-2 py-1 rounded-md text-xs font-medium ${platformColors[ad.platform]}`}>
          {ad.platform === "meta" ? "Meta" : "TikTok"}
        </span>
        <button className="absolute top-3 right-3 p-2 bg-white/90 rounded-lg opacity-0 group-hover:opacity-100 transition hover:bg-white">
          <Bookmark className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-900 truncate">{ad.advertiser_name}</span>
          <span className="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-600">{ad.ad_format}</span>
        </div>
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{ad.copy_text}</p>
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {ad.days_running}d running
          </span>
          <span className="flex items-center gap-1">
            <Globe className="w-3 h-3" />
            {ad.country}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-2">
        <Link
          href={`/ad/${ad.id}`}
          className="flex-1 text-center py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
        >
          View details
        </Link>
        <a
          href={ad.landing_page}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <ExternalLink className="w-4 h-4 text-gray-600" />
        </a>
      </div>
    </div>
  );
}
EOF

cd ..

# ============================================================
# BACKEND (Python FastAPI)
# ============================================================
echo "[2/4] Creating Python backend..."

mkdir -p backend/app/api/routes
mkdir -p backend/app/core
mkdir -p backend/app/scraping
mkdir -p backend/app/ai
mkdir -p backend/app/models
mkdir -p backend/app/schemas

# --- requirements.txt ---
cat > backend/requirements.txt << 'EOF'
fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
pydantic-settings==2.3.0
sqlalchemy==2.0.30
asyncpg==0.29.0
alembic==1.13.0
redis==5.0.0
celery==5.4.0
elasticsearch==8.14.0
anthropic==0.28.0
httpx==0.27.0
python-jose[cryptography]==3.3.0
boto3==1.34.0
Pillow==10.3.0
python-multipart==0.0.9
EOF

# --- main.py ---
cat > backend/app/main.py << 'EOF'
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
EOF

# --- config.py ---
cat > backend/app/core/config.py << 'EOF'
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AdSpy"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://adspy:adspy@localhost:5432/adspy"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    # Clerk
    CLERK_SECRET_KEY: str = ""
    CLERK_PUBLISHABLE_KEY: str = ""

    # Anthropic (Claude API)
    ANTHROPIC_API_KEY: str = ""

    # Bright Data
    BRIGHTDATA_API_KEY: str = ""
    BRIGHTDATA_ZONE: str = ""

    # Cloudflare R2
    R2_ACCESS_KEY: str = ""
    R2_SECRET_KEY: str = ""
    R2_BUCKET: str = "adspy-media"
    R2_ENDPOINT: str = ""
    R2_PUBLIC_URL: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
EOF

# --- Database models ---
cat > backend/app/models/ad.py << 'EOF'
from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class Platform(str, enum.Enum):
    meta = "meta"
    tiktok = "tiktok"
    google = "google"


class AdFormat(str, enum.Enum):
    image = "image"
    video = "video"
    carousel = "carousel"


class Ad(Base):
    __tablename__ = "ads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(Enum(Platform), nullable=False, index=True)
    advertiser_name = Column(Text, nullable=False, index=True)
    advertiser_id = Column(String(255), nullable=False, index=True)
    ad_id = Column(String(255), unique=True, nullable=False)
    country = Column(String(10), nullable=False, index=True)
    language = Column(String(10), nullable=False)
    ad_format = Column(Enum(AdFormat), nullable=False, index=True)
    copy_text = Column(Text, default="")
    cta_text = Column(String(255), default="")
    landing_page = Column(Text, default="")
    media_urls = Column(JSON, default=list)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
EOF

# --- Database setup ---
cat > backend/app/core/database.py << 'EOF'
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
EOF

# --- Ads routes ---
cat > backend/app/api/routes/ads.py << 'EOF'
from fastapi import APIRouter, Query, Depends
from typing import Optional
from app.core.config import settings

router = APIRouter()


@router.get("/search")
async def search_ads(
    q: Optional[str] = Query(None, description="Search query"),
    platform: Optional[str] = Query(None, description="meta or tiktok"),
    format: Optional[str] = Query(None, description="image, video, or carousel"),
    country: Optional[str] = Query(None, description="ISO country code"),
    language: Optional[str] = Query(None),
    sort: str = Query("newest", description="newest, longest_running"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Search ads with filters. Returns paginated results."""
    # TODO: Implement Elasticsearch query
    return {
        "results": [],
        "total": 0,
        "page": page,
        "limit": limit,
    }


@router.get("/trending")
async def trending_ads(
    country: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Get longest-running (likely profitable) ads."""
    return {"results": [], "total": 0}


@router.get("/{ad_id}")
async def get_ad(ad_id: str):
    """Get full ad details."""
    # TODO: Fetch from DB
    return {"error": "Not found"}, 404
EOF

# --- Brands routes ---
cat > backend/app/api/routes/brands.py << 'EOF'
from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter()


@router.get("/search")
async def search_brands(q: str = Query(..., min_length=1)):
    """Search advertisers/brands."""
    return {"results": [], "total": 0}


@router.get("/{brand_id}/ads")
async def get_brand_ads(
    brand_id: str,
    platform: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get all ads for a specific brand."""
    return {"results": [], "total": 0, "page": page}


@router.post("/watchlist")
async def add_to_watchlist(brand_id: str):
    """Add brand to user's watchlist."""
    return {"status": "added"}


@router.get("/watchlist")
async def get_watchlist():
    """Get user's brand watchlist."""
    return {"brands": []}
EOF

# --- AI routes ---
cat > backend/app/api/routes/ai.py << 'EOF'
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ScriptRequest(BaseModel):
    ad_id: str


class CopyRequest(BaseModel):
    product: str
    audience: str
    platform: str = "meta"
    tone: str = "professional"


class AnalyzeRequest(BaseModel):
    ad_id: Optional[str] = None
    copy_text: Optional[str] = None
    media_url: Optional[str] = None


@router.post("/generate-script")
async def generate_script(req: ScriptRequest):
    """Generate hooks + video script from a winning ad."""
    # TODO: Fetch ad, call Claude API
    return {
        "hooks": [
            "Stop scrolling if you want to 3x your ROAS",
            "This ad strategy is making brands in Tunisia rich",
            "POV: You just found your competitor's best ad"
        ],
        "script": "Hook: [Opening line]\n\nProblem: [Identify pain point]\n\nSolution: [Your product]\n\nProof: [Social proof / results]\n\nCTA: [Call to action]",
        "credits_used": 1,
    }


@router.post("/generate-copy")
async def generate_copy(req: CopyRequest):
    """Generate ad copy from product brief."""
    # TODO: Call Claude API
    return {
        "variations": [
            {"headline": "Example headline", "body": "Example body copy", "cta": "Shop Now"}
        ],
        "credits_used": 1,
    }


@router.post("/analyze")
async def analyze_ad(req: AnalyzeRequest):
    """Analyze an ad creative and score it."""
    # TODO: Call Claude API
    return {
        "score": 0,
        "breakdown": {
            "hook_strength": 0,
            "copy_clarity": 0,
            "cta_effectiveness": 0,
        },
        "suggestions": [],
        "credits_used": 1,
    }
EOF

# --- Users routes ---
cat > backend/app/api/routes/users.py << 'EOF'
from fastapi import APIRouter

router = APIRouter()


@router.get("/saved")
async def get_saved_ads():
    """Get user's saved ads and boards."""
    return {"boards": [], "total": 0}


@router.post("/save")
async def save_ad(ad_id: str, board: str = "Default"):
    """Save an ad to a board."""
    return {"status": "saved"}


@router.get("/usage")
async def get_usage():
    """Get user's plan and credit usage."""
    return {
        "plan": "free",
        "searches_today": 0,
        "searches_limit": 20,
        "credits_remaining": 5,
        "credits_limit": 5,
    }
EOF

# --- Init files ---
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/api/routes/__init__.py
touch backend/app/core/__init__.py
touch backend/app/scraping/__init__.py
touch backend/app/ai/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py

# --- Meta scraper stub ---
cat > backend/app/scraping/meta_scraper.py << 'EOF'
"""
Meta Ad Library scraper using Bright Data.

Setup:
  pip install brightdata-sdk
  export BRIGHTDATA_API_KEY=your_key

This scraper fetches ads from the Meta Ad Library for target countries.
"""
import httpx
from datetime import datetime
from app.core.config import settings


MENA_COUNTRIES = ["TN", "DZ", "MA", "EG", "SA", "AE", "KW", "QA", "BH", "OM", "JO", "LB"]


async def scrape_meta_ads(country: str = "TN", limit: int = 100):
    """
    Scrape ads from Meta Ad Library for a given country.
    Uses Bright Data's Web Scraper API for reliable extraction.
    """
    # TODO: Implement with Bright Data SDK
    # 1. Use Bright Data to access Meta Ad Library
    # 2. Parse ad data (creative, copy, advertiser, dates)
    # 3. Download media to R2
    # 4. Return structured ad objects

    print(f"Scraping Meta ads for {country}...")
    return []


async def scrape_all_mena():
    """Scrape ads for all MENA countries."""
    all_ads = []
    for country in MENA_COUNTRIES:
        ads = await scrape_meta_ads(country)
        all_ads.extend(ads)
    return all_ads
EOF

# --- AI script generator stub ---
cat > backend/app/ai/script_generator.py << 'EOF'
"""
AI script generator using Claude API.
Analyzes winning ads and generates hooks + video scripts.
"""
import anthropic
from app.core.config import settings


client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert direct-response copywriter specializing in social media ads
for the MENA market. You write in English, French, and Arabic. You analyze winning ads and
generate scroll-stopping hooks and video scripts that convert.

When generating scripts, follow this structure:
1. HOOK (first 3 seconds) - pattern interrupt that stops the scroll
2. PROBLEM - identify the pain point the audience feels
3. SOLUTION - introduce the product/service as the answer
4. PROOF - social proof, results, testimonials
5. CTA - clear call to action with urgency

Generate 3 hook variations: emotional, curiosity-based, and contrarian."""


async def generate_script(ad_copy: str, advertiser: str, platform: str) -> dict:
    """Generate hooks and video script from a winning ad."""
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""Analyze this winning ad and generate a video script:

Advertiser: {advertiser}
Platform: {platform}
Ad copy: {ad_copy}

Generate:
1. Three hook variations (emotional, curiosity, contrarian)
2. A full 30-60 second video script following the HOOK > PROBLEM > SOLUTION > PROOF > CTA structure
3. Suggested CTA text"""
            }
        ],
    )

    return {
        "raw_response": message.content[0].text,
        "model": "claude-sonnet-4-6",
    }
EOF

# --- Backend .env ---
cat > backend/.env << 'ENVEOF'
DATABASE_URL=postgresql+asyncpg://adspy:adspy@localhost:5432/adspy
REDIS_URL=redis://localhost:6379/0
ELASTICSEARCH_URL=http://localhost:9200
FRONTEND_URL=http://localhost:3000

# Get from https://dashboard.clerk.com
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=

# Get from https://console.anthropic.com
ANTHROPIC_API_KEY=

# Get from https://brightdata.com
BRIGHTDATA_API_KEY=
BRIGHTDATA_ZONE=

# Get from Cloudflare R2
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET=adspy-media
R2_ENDPOINT=
R2_PUBLIC_URL=

# Get from https://dashboard.stripe.com
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
ENVEOF

# ============================================================
# DOCKER COMPOSE
# ============================================================
echo "[3/4] Creating Docker Compose..."

cat > docker-compose.yml << 'EOF'
version: "3.8"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: adspy
      POSTGRES_PASSWORD: adspy
      POSTGRES_DB: adspy
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.14.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - esdata:/usr/share/elasticsearch/data

volumes:
  pgdata:
  esdata:
EOF

# ============================================================
# README
# ============================================================
echo "[4/4] Creating README..."

cat > README.md << 'READMEEOF'
# AdSpy - Ad Intelligence Platform

Ad spy tool for MENA marketers. Search competitor ads across Meta and TikTok, generate winning scripts with AI.

## Quick start

### 1. Start infrastructure
```bash
docker compose up -d
```

### 2. Set up backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Edit .env with your API keys (Clerk, Anthropic, Bright Data, Stripe, R2)

# Run migrations
alembic upgrade head

# Start API
uvicorn app.main:app --reload --port 8000
```

### 3. Set up frontend
```bash
cd frontend
npm install

# Edit .env.local with your Clerk keys

npm run dev
```

### 4. Open http://localhost:3000

## API keys needed

| Service | Get key at | Purpose |
|---------|-----------|---------|
| Clerk | dashboard.clerk.com | Auth |
| Anthropic | console.anthropic.com | AI scripts |
| Bright Data | brightdata.com | Ad scraping |
| Stripe | dashboard.stripe.com | Payments |
| Cloudflare R2 | dash.cloudflare.com | Media storage |

## Architecture

- **Frontend**: Next.js 14 (App Router) + Tailwind + Clerk
- **Backend**: Python FastAPI + Celery
- **Search**: Elasticsearch 8
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis 7
- **Media**: Cloudflare R2
READMEEOF

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. cd adspy"
echo "  2. docker compose up -d"
echo "  3. Add your API keys to backend/.env and frontend/.env.local"
echo "  4. cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo "  5. cd frontend && npm install && npm run dev"
echo ""
