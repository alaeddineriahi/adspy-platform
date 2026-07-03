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
backend/venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```
- API docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health

> Gotchas learned the hard way: `--reload` is flaky on this Windows setup (run
> without it; kill + restart on code changes). Use the **absolute venv python
> path + `--app-dir`** for background launches. `.env` loading is anchored to
> `backend/` in code, so the launch cwd no longer matters.

## 3. Frontend (Next.js, port 3000)
```bash
cd frontend
npm run dev
```
Open http://localhost:3000 → sign up / sign in (Clerk) → you land on `/search`.

> Never run `next build` while `next dev` is running — they share `.next/` and
> the dev server starts 500ing. Stop dev, build, then restart dev.

## What works right now
- **Search** (`/search`): winners-only catalog (~1,000 ads, 6 MENA markets),
  variant-collapsed, money-score ranked, auto-refreshed every 12h
- **Brand Spy** (`/brands` → `/brands/[id]`): money-printing leaderboard + every
  creative a brand runs
- **Media Buyer** (`/mediabuyer`): senior AI co-pilot, streaming chat, tailored
  to the user's budget/market/creatives; grounded in any spied ad via `?ad=<id>`
- **AI Tools** (`/ai`) + ad-detail script generation (Groq now, Claude later)
- **Saved** (`/saved`): per-user swipe file (Postgres)
- **Pricing** (`/pricing`): live plans; checkout wired to Konnect (needs real
  keys); credits metered server-side (free 10 / pro 400 / agency 1500 per month)
- **Admin backoffice** (`/admin`): overview (MRR, credits, catalog), users
  (plan override / credit grants / ban / roles / support impersonation),
  billing, catalog moderation, ingestion, audit log

## Auth (Clerk) — backend verifies everything
The FastAPI backend verifies Clerk session JWTs on every protected route
(`app/core/auth.py`); the issuer/JWKS is derived from `CLERK_PUBLISHABLE_KEY`
in `backend/.env`. AI endpoints spend 1 credit per call and 402 at the cap.
Rate limits: 20/min on AI + media buyer, 240/min general.

### Make yourself (or anyone) an admin
```bash
cd backend
venv/Scripts/python.exe set_admin_role.py you@example.com admin
```
Role lives in Clerk `public_metadata` — no redeploy; also togglable in-app
(Admin → Users → user → role).

## Self-serve ingestion (scraper) — best-performing ads only

The backend pulls ads **on its own** from the public Ad Library and keeps only
the winners. Code lives in `backend/app/ingestion/`:

- `scraper.py`  — Ad Library private GraphQL endpoint (cookie auth)
- `scoring.py`  — keeps only **long-running + scaling + genuine e-commerce**,
  drops the spam flood (games, ebook clickbait, short-drama apps)
- `pipeline.py` — scrape → score → filter → dedup → mirror thumbs to R2 →
  upsert into ES → mark >14d-unseen ads inactive (freshness pass)
- `scheduler.py`— autonomous run every `INGEST_INTERVAL_HOURS` (12h)

> ⚠️ Scraping is against Meta's ToS and can break when Meta changes their
> internal API. The old official `ads_archive` Graph API path was deleted —
> it structurally cannot return MENA commercial ads (political/EU-only).

**The whole ingestion UI + API is admin-only now** (`/admin/ingestion`,
`/api/ingestion/*` behind the Clerk-admin gate). Manage the FB session, capture
the GraphQL search template, trigger sweeps, and watch run stats there. A red
banner appears if a sweep fetches 0 ads (dead cookie) — paste a fresh one.

### Session + template (one-time-ish)
1. **Cookie**: Admin → Ingestion → paste the `Cookie` header from a logged-in
   facebook.com tab (must include `c_user` and `xs`). Persisted to
   `backend/.fb_session.json` (gitignored); tokens auto-refresh every ~3h.
2. **Search template**: on facebook.com/ads/library run any search → DevTools →
   Network → the graphql request with ads → Copy as cURL → paste in the
   "capture the search request" box. Re-capture if sweeps suddenly return 0
   (Meta rotated the `doc_id`).

### Tuning "best performing" (`backend/.env`)
```
INGEST_SCHEDULE_ENABLED=true
INGEST_INTERVAL_HOURS=12
INGEST_MIN_DAYS_RUNNING=7    # longevity gate
INGEST_MIN_VARIANTS=3        # OR scaling gate
INGEST_MAX_PER_COUNTRY=120   # top-scored ads kept per country per sweep
INGEST_STALE_DAYS=14         # unseen this long -> marked inactive
```
`.env` changes need a backend restart to reach the scheduler.

## Payments (Konnect/Flouci — Tunisia)
The full pipe is built: checkout → `payment_intents` row → webhook re-verifies
with the gateway → subscription activated (31 days) → credit cap raised.
Blocked only on real gateway keys (`KONNECT_API_KEY` etc. in `backend/.env`);
until then `/subscribe` returns a clean 503. Strategy lives in `PRICING.md`,
cost ledger in `COSTS.md` — both are living documents.

## Switching AI to Claude (production quality)
In `backend/.env`:
```
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```
(Enable prompt caching when doing this — see COSTS.md §5.)

## Security
API keys were pasted into chat during setup. Rotate the Clerk, Groq, Meta, and
R2 keys before any real deployment. `.env` files are gitignored.
