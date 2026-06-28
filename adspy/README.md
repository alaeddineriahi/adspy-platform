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
