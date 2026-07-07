# Web-research API for the Brand Hunter (optional)

The Brand Hunter discovers winning brands from **TikTok** and **rising scalers**
out of the box — no key needed. Adding a web-search key turns on a **third**
discovery source: live open-web trend research ("best-selling dropshipping
products July 2026", etc.), where the LLM extracts brand names **from the fresh
results** (never from stale training data).

## Where to get a key (pick one)

| Provider | Free tier | Best for | Get the key |
|---|---|---|---|
| **Serper** (recommended) | 2,500 free searches, then ~$50 / 50k | Cheapest raw Google results; simplest | https://serper.dev → sign up → **API Keys** |
| **Tavily** | 1,000 credits/mo free | AI-native (returns clean page content), great for extraction | https://tavily.com → sign up → **API Keys** |
| **Brave Search** | 2,000 queries/mo free | Privacy-friendly, independent index | https://brave.com/search/api/ → subscribe (free plan) → **API Keys** |

The hunter runs ~3 queries per pass (once a day) = ~90 searches/month, so **every
free tier above covers it comfortably.** Serper is the least-effort choice.

## Wiring it in

Add to `backend/.env`:

```env
SEARCH_API_PROVIDER=serper      # serper | tavily | brave
SEARCH_API_KEY=your_key_here
```

Restart the backend. That's it — the next Brand Hunter run (daily, or trigger
`POST /api/ingestion/brand-hunter/run`) will include web-discovered brands.
Leave `SEARCH_API_KEY` empty and the feature stays off; TikTok + rising-scaler
discovery keep working regardless.

## Notes
- Queries are date-stamped (current month/year) so results are current, not evergreen.
- The LLM only extracts names present in the fetched text — this is deliberate,
  so discovery never drifts into an LLM's outdated idea of "popular brands."
- Extracted names still go through `resolve_page_id` (Ad Library), so a name
  that doesn't run Meta ads is simply skipped — no junk enters the catalog.
