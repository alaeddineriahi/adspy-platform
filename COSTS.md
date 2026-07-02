# AdSpy — Running Cost Ledger

> Living document. Updated as features land, until the app reaches its final
> development state. **Last updated: 2026-06-29.**
> Claude prices below are per **1M tokens**, cached from the `claude-api` skill
> (as of 2026-06-04) — verify against <https://platform.claude.com/pricing>.

---

## TL;DR — what does switching to Claude cost?

- **There is no fixed cost.** Claude is pure usage-based billing. Today, on Groq's
  free dev tier, our LLM spend is **$0**. Flipping `AI_PROVIDER=anthropic` only
  starts costing money once real traffic flows.
- **At our current volume (dev/testing), it's cents** — a few dollars a month at most.
- The two things that move the number: **which model** we pick, and whether we turn
  on **prompt caching** (not yet implemented — see §4). Caching roughly **halves**
  the media-buyer cost because our ~2,900-token persona+playbook is identical on
  every message.
- **Recommendation:** media buyer on **Sonnet 4.6** (best reasoning-per-dollar for
  advice) with prompt caching; **Haiku 4.5** for the high-volume AI-Tools
  generators; keep **Groq free** for local dev. See §5.

---

## 1. Where we spend LLM tokens

| Surface | File | Call shape | Frequency |
|---|---|---|---|
| Media Buyer chat | `app/ai/media_buyer.py` | streaming chat, ~2.9k system + history + output | per user message |
| AI Tools (video script / copy / analyze) | `app/ai/script_generator.py` | single-shot, ~0.8k in / up to 2k out | per generation |
| Ingestion / scoring / scraping | `app/ingestion/*` | **no LLM** (regex + Meta GraphQL) | — |

The media buyer is the cost center. Ingestion is free of LLM cost by design.

## 2. Claude model pricing (per 1M tokens)

| Model | Input | Output | Notes |
|---|---|---|---|
| Claude Opus 4.8 | $5.00 | $25.00 | most capable; overkill for advice |
| **Claude Sonnet 4.6** | **$3.00** | **$15.00** | best quality/cost balance — recommended default |
| Claude Haiku 4.5 | $1.00 | $5.00 | cheapest; great for bulk AI-Tools gens |
| Claude Fable 5 | $10.00 | $50.00 | frontier; not needed here |
| Groq Llama 3.3 70B | ~free (dev) | ~free (dev) | current provider; rate-limited |

Prompt caching: cache **read ≈ 0.1×** input price, cache **write ≈ 1.25×** (5-min TTL).

## 3. Per-interaction cost estimates

Assumes media-buyer message = ~2,900 system + ~120 profile + ~800 history + ~100 user in, ~500 out.
AI-Tools generation = ~800 in, ~1,200 out. ("cached" = system prompt served from cache.)

| Interaction | Opus 4.8 | Sonnet 4.6 | Haiku 4.5 |
|---|---|---|---|
| Media-buyer message (no cache) | ~3.3¢ | ~2.0¢ | ~0.65¢ |
| Media-buyer message (cached) | ~1.9¢ | ~1.2¢ | ~0.4¢ |
| AI-Tools generation | ~3.4¢ | ~2.0¢ | ~0.7¢ |

## 4. Monthly projections (media buyer, with prompt caching)

| Volume | Opus 4.8 | Sonnet 4.6 | Haiku 4.5 |
|---|---|---|---|
| Dev/testing now (~200 msgs/mo) | ~$4 | ~$2 | ~$1 |
| Small launch (~3,000 msgs/mo) | ~$57 | **~$36** | ~$12 |
| Growth (~30,000 msgs/mo) | ~$570 | **~$360** | ~$120 |

Without caching, multiply the media-buyer numbers by ~1.7×. **Prompt caching is not
yet wired in** — `script_generator.stream_llm()` sends the system prompt uncached on
every call. Adding `cache_control` on the persona+playbook prefix (Anthropic path) is
the single highest-ROI cost optimization; do it before scaling traffic.

## 5. Recommendation

1. **Dev:** stay on Groq (`AI_PROVIDER=groq`) — free, fast enough for building.
2. **Production media buyer:** `AI_PROVIDER=anthropic` → **Sonnet 4.6** (already the
   model hardcoded in `_call_claude` / `_stream_claude`). Bump to Opus 4.8 only if
   advice quality demands it; the playbook does most of the heavy lifting, so Sonnet
   is plenty.
3. **AI-Tools generators:** consider **Haiku 4.5** for copy/script/analyze — high
   volume, lower reasoning bar. (Would need a per-call model override, not built yet.)
4. **Turn on prompt caching** before real traffic (see §4).
5. Add a hard monthly spend cap / alert in the Anthropic console once live.

## 6. Infrastructure costs "until this point"

Everything is on local Docker + free tiers → **effectively $0/mo today.**

| Service | Now (dev) | Free-tier ceiling | Cost when we exceed it |
|---|---|---|---|
| Groq (LLM) | $0 | rate-limited dev tier | switch to Claude (§2) |
| Cloudflare R2 (thumbnails) | $0 | 10 GB storage, 1M/10M ops | $0.015/GB-mo, **$0 egress** |
| Clerk (auth) | $0 | 10,000 MAU | ~$25/mo + $0.02/MAU after |
| Postgres / Elasticsearch / Redis | $0 (local Docker) | — | managed/VPS hosting in prod (ES is the pricey one; plan to self-host on a VPS) |
| Meta Ad Library scraping | $0 | — | free (cookie session) |
| Domain + app hosting | $0 (localhost) | — | ~$5–20/mo VPS + ~$12/yr domain |

**Not yet incurred:** production hosting, managed databases, a paid Anthropic plan.
The first real bill will be whichever comes first: Anthropic usage or a production VPS.

## 7. Decisions & change log

| Date | Change | Cost impact |
|---|---|---|
| 2026-06-29 | Baseline: Groq free, all infra local/free. LLM spend $0. | — |
| 2026-06-29 | Media-buyer playbook added (~1,984 tok) → system prompt now ~2,900 tok/msg. | raises per-msg input; makes caching high-value |
| 2026-07-02 | **Credit enforcement + rate limits live**: AI endpoints require Clerk auth, spend 1 credit each (free=10/mo), and are capped at 20 req/min per user. | Caps worst-case LLM spend per free user at ~10 generations/month; abuse (scripted hammering) now bounded — projections in §4 become hard ceilings. |
| _next_ | _e.g. enable prompt caching / flip to Sonnet 4.6 / go to production_ | _fill in_ |
