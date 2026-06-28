# AdSpy Platform - Architecture & V1 Spec

**Target market:** Tunisia (launch) > MENA (expansion)
**Model:** GetHookd-style ad intelligence SaaS
**Date:** June 25, 2026

---

## Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14 (App Router) | SSR for SEO, React Server Components, fast DX |
| Auth | Clerk | Arabic locale support, social login, fast integration |
| Backend API | Python FastAPI | Best for scraping (Bright Data SDK), AI APIs, async perf |
| Task queue | Celery + Redis | Background scraping jobs, scheduled indexing |
| Search | Elasticsearch | Full-text across millions of ads, Arabic support, faceted filters |
| Database | PostgreSQL | Users, plans, ads metadata, saved boards |
| Cache | Redis | Search result caching, rate limiting, sessions |
| Media storage | Cloudflare R2 | Ad screenshots/videos, no egress fees |
| AI (dev) | Groq (Llama 3.3 70B) | Free tier, fast inference. Swap to Claude API for production |
| AI (prod) | Claude API (Anthropic) | One config change: AI_PROVIDER=anthropic |
| Scraping | Bright Data | Meta Ad Library, TikTok Creative Center, bot bypass, MENA proxies |
| Payments | Konnect (primary) | TND native, bank cards + E-Dinar + wallet, 1.3% local fees |
| Payments | Flouci (secondary) | Mobile wallets, Flouci Wallet, 1.3% local fees |
| Hosting | Vercel (frontend) + Railway (API) | Easy deploys, auto-scaling |

---

## V1 features (MVP scope)

### Phase 1: Ad library + search (Weeks 1-4)

**Ad scraping pipeline**
- Scrape Meta Ad Library (Facebook + Instagram ads) via Bright Data
- Scrape TikTok Creative Center for TikTok ads
- Store ad metadata: creative type, copy text, CTA, landing page URL, advertiser name, country, language, start date, platform
- Save ad media (images/videos) to R2
- Scheduled Celery jobs running every 6 hours to index new ads
- Focus on MENA region ads first (Tunisia, Algeria, Morocco, Egypt, Saudi, UAE)

**Search & discovery**
- Full-text search across ad copy, advertiser name, landing page domain
- Filters: platform (Meta/TikTok), country, language (Arabic/French/English), ad format (image/video/carousel), date range
- Sort by: newest, longest running (proxy for performance), most engagement
- Ad detail view: full creative, copy, CTA, landing page screenshot, run duration
- "Longest running" = ads active for 30+ days (proxy for profitable ads)

**User system**
- Clerk auth with email + Google sign-in
- Free tier: 20 searches/day, basic filters
- Pro tier (29 TND/month): unlimited search, all filters, save ads
- Save ads to boards/collections (persist even when ad goes offline)

### Phase 2: Brand spy (Weeks 5-6)

- Enter any brand/advertiser name or domain
- See all their active ads across platforms
- Track how many ads they're running, which formats, which countries
- Landing page tracking: screenshot + URL for each ad
- "Brand watchlist" - get notified when a brand launches new ads

### Phase 3: AI creative tools (Weeks 7-8)

- **AI script generator**: Select any winning ad > AI generates 3 hook variations + full video script based on the ad's strategy
- **Ad copy generator**: Input your product + target audience > generates ad copy inspired by top-performing ads in your niche
- **Creative analyzer**: Upload your ad > AI scores it on hook strength, copy clarity, CTA effectiveness, and suggests improvements
- Credit-based system: free tier gets 5 AI generations/month, Pro gets 50

---

## Data models

### ads
```
id              UUID (PK)
platform        ENUM (meta, tiktok, google)
advertiser_name TEXT
advertiser_id   TEXT (platform-specific)
ad_id           TEXT (platform-specific, unique)
country         TEXT (ISO 3166-1)
language        TEXT (ISO 639-1)
ad_format       ENUM (image, video, carousel)
copy_text       TEXT
cta_text        TEXT
landing_page    TEXT (URL)
media_urls      JSONB (array of R2 URLs)
first_seen      TIMESTAMP
last_seen       TIMESTAMP
is_active       BOOLEAN
metadata        JSONB (platform-specific fields)
created_at      TIMESTAMP
```

### users
```
id              UUID (PK)
clerk_id        TEXT (unique)
email           TEXT
plan            ENUM (free, pro, agency)
credits_remaining INT
country         TEXT
created_at      TIMESTAMP
```

### saved_ads
```
id              UUID (PK)
user_id         UUID (FK > users)
ad_id           UUID (FK > ads)
board_name      TEXT
created_at      TIMESTAMP
```

### brands_watchlist
```
id              UUID (PK)
user_id         UUID (FK > users)
advertiser_name TEXT
advertiser_id   TEXT
platform        TEXT
created_at      TIMESTAMP
```

### ai_generations
```
id              UUID (PK)
user_id         UUID (FK > users)
type            ENUM (script, copy, analysis)
input_ad_id     UUID (FK > ads, nullable)
input_text      TEXT
output          JSONB
credits_used    INT
created_at      TIMESTAMP
```

---

## API endpoints

### Ads
- `GET /api/ads/search` - Search ads with filters (paginated)
- `GET /api/ads/:id` - Get ad detail
- `GET /api/ads/trending` - Get trending/longest running ads

### Brands
- `GET /api/brands/search` - Search advertisers
- `GET /api/brands/:id/ads` - Get all ads for a brand
- `POST /api/brands/watchlist` - Add brand to watchlist
- `GET /api/brands/watchlist` - Get user's watchlist

### AI
- `POST /api/ai/generate-script` - Generate hooks + script from an ad
- `POST /api/ai/generate-copy` - Generate ad copy from product brief
- `POST /api/ai/analyze` - Analyze an ad creative

### Payments
- `GET /api/payments/plans` - Get available plans with TND pricing
- `POST /api/payments/subscribe` - Create payment link (Konnect or Flouci)
- `GET /api/payments/webhook/konnect` - Konnect webhook callback
- `GET /api/payments/verify/:id` - Verify Flouci payment status

### User
- `GET /api/user/saved` - Get saved ads/boards
- `POST /api/user/save` - Save ad to board
- `GET /api/user/usage` - Get credit usage

---

## Scraping architecture

```
Celery Beat (scheduler)
  |
  v
Celery Workers (N workers)
  |
  v
Bright Data SDK (Python)
  |- Meta Ad Library API / scraper
  |- TikTok Creative Center scraper
  |
  v
Processing pipeline:
  1. Deduplicate (check ad_id exists)
  2. Extract text (OCR if needed)
  3. Download media > upload to R2
  4. Index to Elasticsearch
  5. Store metadata to PostgreSQL
```

**Scraping schedule:**
- Full index: weekly (all active ads in target countries)
- Incremental: every 6 hours (new ads only)
- Brand watchlist: every 2 hours (only watched brands)

---

## MENA-specific considerations

**Languages:** Arabic (RTL), French, English - all UI and search must support these three
**Payment:** Konnect (primary) for card + E-Dinar subscriptions, Flouci (secondary) for mobile wallet users. All prices in TND. No Stripe needed.
**Ad libraries:** Meta Ad Library has strong MENA coverage. TikTok Creative Center covers MENA but is thinner
**Proxies:** Bright Data residential proxies in Tunisia, Morocco, Egypt, Saudi, UAE for region-accurate scraping
**SEO:** Target keywords in French + Arabic ("outils espionnage publicitaire", "مكتبة الإعلانات")

---

## Pricing (suggested)

| Plan | Price (TND) | Searches | AI credits | Saved ads | Brand spy |
|------|-------------|----------|------------|-----------|-----------|
| Free | 0 | 20/day | 5/month | 10 | No |
| Pro | 29/month | Unlimited | 50/month | Unlimited | 5 brands |
| Agency | 79/month | Unlimited | 200/month | Unlimited | 25 brands |

Annual billing: 2 months free. Payment via Konnect (cards/E-Dinar) or Flouci (mobile wallet).

---

## Project structure

```
adspy/
  frontend/                 # Next.js 14
    app/
      (auth)/              # Clerk auth pages
      (dashboard)/
        search/            # Ad search + results
        ad/[id]/           # Ad detail view
        brands/            # Brand spy
        ai/                # AI tools
        saved/             # Saved ads & boards
        settings/          # Account + billing
      api/                 # Next.js API routes (proxy to FastAPI)
    components/
    lib/
  
  backend/                  # Python FastAPI
    app/
      api/
        routes/
          ads.py
          brands.py
          ai.py
          payments.py       # Konnect + Flouci
          users.py
      core/
        config.py
        auth.py           # Clerk JWT verification
        elasticsearch.py
      scraping/
        meta_scraper.py
        tiktok_scraper.py
        pipeline.py       # Processing + dedup
      ai/
        script_generator.py
        copy_generator.py
        analyzer.py
      models/
      schemas/
    celery_app.py
    requirements.txt

  docker-compose.yml        # Postgres, Redis, Elasticsearch, API
  .env
```

---

## Build order

1. **Week 1:** Project setup - Next.js + FastAPI scaffold, Clerk auth, Postgres + Redis via Docker, Konnect/Flouci payment integration
2. **Week 2:** Scraping pipeline 