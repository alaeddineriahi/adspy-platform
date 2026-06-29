# Running AdSpy locally

Everything is wired up. Here's how to start/stop the stack and known gotchas.

## Prerequisites (already installed on this machine)
- Node 24, Python 3.12, Docker Desktop (running)

## 1. Infrastructure (Postgres, Redis, Elasticsearch)
```bash
docker compose up -d
```
> Postgres is published on host port **5433** (not 5432) because a local
> PostgreSQL 17 Windows service already owns 5432. The backend `DATABASE_URL`
> points at 5433 to match.

## 2. Backend (FastAPI, port 8000)
```bash
cd backend
venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health

Seed sample ads into Elasticsearch (one-time / anytime):
```bash
cd backend
venv/Scripts/python.exe seed.py
```

## 3. Frontend (Next.js, port 3000)
```bash
cd frontend
npm run dev
```
Open http://localhost:3000 → sign up / sign in (Clerk) → you land on `/search`.

## What works right now
- **Search** (`/search`): full-text + filters over Elasticsearch (8 seeded MENA ads)
- **Brand Spy** (`/brands`): advertiser aggregation from the ads index
- **AI Tools** (`/ai`): real ad-copy generation via Groq (Llama 3.3 70B)
- **Ad detail** (`/ad/[id]`): view ad + "Generate AI script"
- **Payments**: disabled for now (per request); `/api/payments/plans` still returns pricing

## Meta Ad Library (real data source)

There are **two** Meta paths, and only one returns MENA commercial ads:

1. **Raw `ads_archive` Graph API** (`backend/app/scraping/meta_official.py`,
   `POST /api/ads/ingest`). With our token this returns `error_subcode 2332002`
   for **every** country/version/ad_type — including Germany. Per Meta's own
   [Ad Library API page](https://www.facebook.com/ads/library/api), this endpoint
   only exposes *political/issue ads worldwide* + *all ad types for UK/EU only*.
   So it's a **genuine dead end for MENA commercial ads** — not a token/code bug.

2. **Authorized Ad Library search** (the path that actually works). It returns
   the full commercial library for MENA (TN ~4M, AE ~290k, SA, EG, MA ads). This
   is what we used to load real data.

### Loading real MENA ads
Real ads are pulled via the authorized Ad Library search and indexed by:
```bash
cd backend
venv/Scripts/python.exe seed_real.py
```
This seeds **38 real, live MENA ads** (TN/AE/SA/EG/MA — cosmetics, furniture,
fashion, eyewear, apps, games, dropshipping). Re-running is idempotent.

> Field limitation: the Ad Library search returns advertiser, link title, dates,
> snapshot URL and currency — **not** full body copy or the image/video files
> (those live behind each `ad_snapshot_url`). So `copy_text` falls back to the
> link title (or page name when blank), and `media_urls` is empty.

## Self-serve ingestion (scraper) — best-performing ads only

The backend can now pull ads **on its own** from the public Ad Library and keep
only the winners. Code lives in `backend/app/ingestion/`:

- `scraper.py`  — talks to the Ad Library's private search endpoint (cookie auth)
- `scoring.py`  — keeps only **long-running + scaling + genuine e-commerce** ads,
  and filters out the spam that floods the library (mobile games, ebook/novel
  clickbait, short-drama apps, generic app installs)
- `pipeline.py` — scrape → score → filter → dedup → upsert into Elasticsearch
- `scheduler.py`— optional autonomous run every `INGEST_INTERVAL_HOURS`

> ⚠️ This is **scraping** — against Meta's ToS, can break when Meta changes their
> internal API, and needs a logged-in session. You chose this route knowingly.

### 1. Give the scraper a Facebook session
The backend resolves a session in this order (`app/ingestion/session.py`):
env override → browser auto-read → disk cache. It bootstraps the `fb_dtsg`/`lsd`
tokens itself, caches to `backend/.fb_session.json` (gitignored), and refreshes
on auth failure. With no session, ingestion is a safe **no-op** (0 ads, never
crashes). Check `GET /api/ingestion/status` → `session.source` /`session.error`.

Pick the path that matches your browser:

**A) Paste once (works everywhere — recommended for Opera GX / Chrome / Edge).**
Those browsers use *app-bound cookie encryption*, which `browser-cookie3` can't
decrypt from a normal process (you'll see `RequiresAdminError`). So paste once:
- Open the **Ingestion** page → "Paste your Facebook cookie" box.
- In a logged-in facebook.com tab: DevTools → Network → click any request →
  Headers → copy the **Cookie** value (must include `c_user` and `xs`).
- Paste → **Save session**. Persisted to disk, lasts ~months. No `.env`, no restart.

**B) Browser auto-read (Firefox only, hands-free).** Firefox has no app-bound
encryption, so just stay logged into facebook.com in Firefox and set:
```
SCRAPER_USE_BROWSER_COOKIES=true
SCRAPER_BROWSER=firefox     # or auto
```

**C) .env override.** `META_FB_COOKIE=<full Cookie header>` (+ optional
`META_FB_DTSG`). Equivalent to A but via file; needs a restart.

Relevant `.env` toggles:
```
SCRAPER_USE_BROWSER_COOKIES=false  # true only for Firefox auto-read
SCRAPER_BROWSER=opera_gx           # auto|chrome|edge|firefox|brave|opera|opera_gx
SCRAPER_COOKIE_FILE=               # explicit Cookies DB path (rarely needed)
SCRAPER_PROXY=                     # optional http(s) proxy, recommended for volume
```

### 1b. Capture the search request (one-time, required)
Meta retired the old scrape endpoint; the live Ad Library uses `/api/graphql/`
with a rotating `doc_id` that can't be guessed. Capture your browser's real
request once (parsed locally — your cookie never leaves the machine):
1. Go to **facebook.com/ads/library**, run any search (pick a country + keyword)
2. DevTools (F12) → **Network** → filter `graphql`
3. Click the request whose **response contains ads**, then right-click →
   **Copy → Copy as cURL**
4. Paste it into the **"capture the search request"** box on the Ingestion page →
   Save. (Re-capture if ingestion suddenly returns 0 — Meta rotated the doc_id.)

### 2. Trigger a sweep
```bash
# inline (waits, returns stats)
curl -X POST localhost:8000/api/ingestion/run -H "Content-Type: application/json" \
  -d '{"wait": true, "countries": ["TN","MA"], "search_terms": ["livraison gratuite","promo"]}'

# background (poll status)
curl -X POST localhost:8000/api/ingestion/run -H "Content-Type: application/json" -d '{}'
curl localhost:8000/api/ingestion/status
curl localhost:8000/api/ingestion/config
```
Leave `countries`/`search_terms` out to use the built-in MENA defaults.

### 3. Make it autonomous (self-serve)
In `backend/.env`:
```
INGEST_SCHEDULE_ENABLED=true
INGEST_INTERVAL_HOURS=12
```
Restart — the pipeline then runs every 12h with no manual trigger.

### Tuning "best performing"
```
INGEST_MIN_DAYS_RUNNING=7    # min days an ad must have run (longevity gate)
INGEST_MIN_VARIANTS=3        # OR min duplicate variants (scaling gate)
INGEST_MAX_PER_COUNTRY=40    # cap of top-scored ads kept per country per sweep
```
An ad is kept only if it's **e-commerce** (not spam) **and** (`days_running ≥
MIN_DAYS` **or** `variant_count ≥ MIN_VARIANTS`). Spam categories are dropped
even if they're long-running. Verify the logic anytime with:
```bash
cd backend && venv/Scripts/python.exe verify_ingestion.py
```

## Switching AI to Claude (production quality)
In `backend/.env`:
```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

## Security
API keys were pasted into chat during setup. Rotate the Clerk, Groq, Meta, and R2
keys before any real deployment. `.env` files are gitignored.
