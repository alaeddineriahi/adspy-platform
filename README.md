# AdSpy Platform 🔍

**AI-powered ad intelligence platform for the MENA market.**

Discover winning ads, spy on competitors, and generate high-converting ad scripts — built for Tunisia and the MENA region.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Next.js](https://img.shields.io/badge/Next.js-14-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB)

---

## What is AdSpy?

AdSpy is a GetHookd-style ad research platform that lets marketers and agencies:

- **Search 100K+ ads** across Meta (Facebook/Instagram) and TikTok
- **Spy on competitors** — track any brand's ad activity in real-time
- **Generate AI scripts** — turn any winning ad into hooks + video scripts
- **Analyze creatives** — AI scores your ads on hook strength, copy clarity, CTA effectiveness
- **Save & organize** — board system to collect winning ads for reference

### Built for Tunisia & MENA

- All prices in **TND** (Tunisian Dinar)
- Payments via **Konnect** (cards/E-Dinar) and **Flouci** (mobile wallets)
- Trilingual search: **Arabic (RTL) + French + English**
- Ad scraping focused on MENA countries (TN, DZ, MA, EG, SA, AE, etc.)

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | Next.js 14 (App Router) | SSR, React Server Components |
| Auth | Clerk | Arabic locale, social login |
| Backend | Python FastAPI | Async, scraping, AI integration |
| Search | Elasticsearch 8 | Multilingual full-text, Arabic analyzer |
| Database | PostgreSQL 16 | Users, ads metadata, saved boards |
| Cache/Queue | Redis 7 + Celery | Background scraping jobs |
| Media | Cloudflare R2 | Ad images/videos, no egress fees |
| AI (dev) | Groq (Llama 3.3 70B) | Free tier — zero cost |
| AI (prod) | Claude API (Anthropic) | One config swap |
| Scraping | Bright Data | Meta Ad Library, TikTok Creative Center |
| Payments | Konnect + Flouci | TND native, 1.3% fees |
| Hosting | Vercel + Railway | Frontend + API |

---

## Prerequisites

Before you start, make sure you have:

- **Node.js 18+** — [Download](https://nodejs.org/)
- **Python 3.11+** — [Download](https://python.org/)
- **Docker & Docker Compose** — [Download](https://docker.com/)
- **Git** — [Download](https://git-scm.com/)

### Free API Keys (required)

| Service | Sign up | What for |
|---------|---------|----------|
| **Groq** | [console.groq.com](https://console.groq.com) | AI script generation (free) |
| **Clerk** | [clerk.com](https://clerk.com) | Authentication (free <10K users) |
| **Konnect** | [konnect.network](https://konnect.network) | Payments — use sandbox mode (free) |
| **Cloudflare R2** | [dash.cloudflare.com](https://dash.cloudflare.com) | Media storage (free 10GB) |

### Paid API Keys (optional for dev)

| Service | Sign up | What for |
|---------|---------|----------|
| **Bright Data** | [brightdata.com](https://brightdata.com) | Ad scraping (has trial credits) |
| **Flouci** | [flouci.com](https://flouci.com) | Mobile wallet payments |

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/alaeddineriahi/adspy-platform.git
cd adspy-platform
```

### 2. Run the setup script

```bash
chmod +x setup_adspy.sh
./setup_adspy.sh
```

This creates the full project scaffold: frontend, backend, Docker config, and all boilerplate.

### 3. Copy implementation files

The `src/` directory contains the actual implementation code. Copy these files into the scaffold:

```bash
# Backend files
cp -r src/backend/app/ai/* backend/app/ai/
cp -r src/backend/app/api/routes/* backend/app/api/routes/
cp -r src/backend/app/core/* backend/app/core/
cp -r src/backend/app/scraping/* backend/app/scraping/
cp -r src/backend/app/payments/* backend/app/payments/
```

### 4. Configure environment variables

```bash
# Backend
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Frontend
cp frontend/.env.example frontend/.env.local
# Edit frontend/.env.local with your Clerk keys
```

See [Environment Variables](#environment-variables) below for all required values.

### 5. Start infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL, Redis, and Elasticsearch.

### 6. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) — you're live!

---

## Environment Variables

### Backend (`backend/.env`)

```env
# App
APP_NAME=AdSpy
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://adspy:adspy@localhost:5432/adspy

# Redis
REDIS_URL=redis://localhost:6379/0

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# Auth (Clerk)
CLERK_SECRET_KEY=sk_test_xxxxx
CLERK_PUBLISHABLE_KEY=pk_test_xxxxx

# AI — "groq" (free) or "anthropic" (paid)
AI_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxx
ANTHROPIC_API_KEY=              # leave empty for dev

# Scraping (Bright Data)
BRIGHTDATA_API_KEY=
BRIGHTDATA_CUSTOMER_ID=

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET_NAME=adspy-media
R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com

# Payments — Konnect (primary)
KONNECT_API_KEY=your_konnect_api_key
KONNECT_WALLET_ID=your_wallet_id
KONNECT_SANDBOX=true

# Payments — Flouci (secondary)
FLOUCI_APP_TOKEN=your_flouci_token
FLOUCI_APP_SECRET=your_flouci_secret
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
CLERK_SECRET_KEY=sk_test_xxxxx
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/search
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/search
```

---

## Project Structure

```
adspy-platform/
  frontend/                     # Next.js 14
    src/
      app/
        (auth)/                 # Clerk sign-in/sign-up
        (dashboard)/
          search/               # Ad search + results grid
          ad/[id]/              # Ad detail + AI script gen
          brands/               # Brand spy
          ai/                   # AI creative tools
          saved/                # Saved ads & boards
          settings/             # Account + billing
      components/
        ads/                    # AdCard, AdGrid, etc.
      lib/                      # API client, utils
      types/                    # TypeScript interfaces

  backend/                      # Python FastAPI
    app/
      api/routes/
        ads.py                  # Search, trending, detail
        ai.py                   # Script gen, copy gen, analysis
        payments.py             # Konnect + Flouci integration
        brands.py               # Brand spy endpoints
        users.py                # User management
      core/
        config.py               # Environment config
        elasticsearch.py        # ES client + multilingual index
      scraping/
        meta_scraper.py         # Bright Data Meta Ad Library
        pipeline.py             # Dedup, media upload, indexing
      payments/
        konnect.py              # Konnect API client
        flouci.py               # Flouci API client
      ai/
        script_generator.py     # Groq/Claude AI abstraction
      models/                   # SQLAlchemy models

  src/                          # Implementation source files
    backend/                    # Drop into backend/
    frontend/                   # Drop into frontend/

  docker-compose.yml            # Postgres, Redis, Elasticsearch
  setup_adspy.sh                # One-command project scaffold
  docs/
    architecture.md             # Full architecture spec
```

---

## API Endpoints

### Ads
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ads/search` | Search ads with filters |
| GET | `/api/ads/trending` | Get longest-running ads |
| GET | `/api/ads/{id}` | Get ad detail |

### AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/generate-script` | Generate hooks + script from ad |
| POST | `/api/ai/generate-copy` | Generate ad copy from brief |
| POST | `/api/ai/analyze` | Score ad creative |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/payments/plans` | Get plans with TND pricing |
| POST | `/api/payments/subscribe` | Create payment (Konnect/Flouci) |
| GET | `/api/payments/webhook/konnect` | Konnect webhook |
| GET | `/api/payments/verify/{id}` | Verify Flouci payment |

### Brands
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/brands/search` | Search advertisers |
| GET | `/api/brands/{id}/ads` | Get brand's ads |
| POST | `/api/brands/watchlist` | Watch a brand |

---

## Pricing Plans

| Plan | Price | Searches | AI Credits | Brand Spy |
|------|-------|----------|------------|-----------|
| Free | 0 TND | 20/day | 5/month | No |
| Pro | 29 TND/month | Unlimited | 50/month | 5 brands |
| Agency | 79 TND/month | Unlimited | 200/month | 25 brands |

Annual billing: 2 months free.

---

## Switching AI Provider

During development, the app uses **Groq** (free, Llama 3.3 70B). To switch to **Claude API** for production:

```env
# In backend/.env, change:
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

That's it. Same prompts, same JSON output, better quality.

---

## Development Roadmap

| Week | Milestone |
|------|-----------|
| 1 | Project setup, auth, payments |
| 2 | Scraping pipeline (Meta Ad Library) |
| 3 | Search engine + UI |
| 4 | User features, billing, tier gates |
| 5-6 | Brand spy + watchlist |
| 7-8 | AI tools (scripts, copy, analysis) |
| 9 | RTL, i18n, SEO, Tunisia launch |

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add my feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

Built with ❤️ for the Tunisian & MENA marketing community.
