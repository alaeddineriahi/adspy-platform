# AdSpy — Subscription Pricing Strategy

> Living document. Re-tune the tiers **every time we ship a feature that adds value
> or cost.** Pairs with [COSTS.md](COSTS.md) (what a user costs us) — this file is
> what we charge them. **Last updated: 2026-06-29.**
> Recommended numbers below; final price points are the founder's call. The code
> (`payments.py` `/plans` + `konnect.PLAN_PRICES`) currently holds placeholders that
> should be synced once numbers are locked (see §7).

---

## 1. Positioning — what are we actually selling?

Not "ad data." We sell **two outcomes a MENA  e-commerce seller pays real money for:**
1. **Find winning products/ads** they can't find in global tools (MENA/Arabic/French,
   money-ranked) → less guessing.
2. **Don't burn ad budget** — the AI media buyer turns a winner into a plan and stops
   them wasting 15–50 TND/day tests that would've failed.

**Anchor to ad spend, not to our cost.** A seller spending 500–3,000 TND/mo on ads
saves multiples of the subscription the first time we help them skip one dead product
or scale one winner. Price against that value, keep it accessible in local terms.

**Primary market:** Tunisia first (Konnect/Flouci, TND), then MENA (MA/DZ/EG/Gulf).
Show **TND for the home market and ~USD for international** buyers.

## 2. What's monetizable *right now* (feature → gating)

| Feature (built) | Free | Pro | Agency |
|---|---|---|---|
| Search money-ranked winners | limited (25 results, 1 country) | ✅ unlimited, all countries/filters | ✅ |
| Brand Spy leaderboard | top 5 only | ✅ full | ✅ |
| Media Buyer co-pilot (AI) | ✅ metered (credits) | ✅ metered | ✅ metered |
| AI Tools (script/copy/analyze) | ✅ metered (credits) | ✅ metered | ✅ metered |
| Saved boards | 10 | ✅ unlimited | ✅ unlimited |
| Self-serve ingestion (custom keyword scrapes) | ✗ | ✗ | ✅ |
| Seats | 1 | 1 | 3 |

**The metered lever = "AI credits."** Search/Brand Spy are ~free to serve, so they're
unlimited on paid tiers. The **only real variable cost is AI** (media buyer + AI tools),
so that's what credits gate.

- **1 AI credit = 1 media-buyer message OR 1 AI-tools generation.**
- Our cost per credit ≈ **1–2¢** (Sonnet 4.6 + caching, per COSTS.md). Credits exist to
  protect margin at the top end, not to nickel-and-dime normal use — set them generous.

## 3. Recommended tiers

| Tier | TND/mo | ~USD | AI credits/mo | Best for |
|---|---|---|---|---|
| **Free** | 0 | $0 | 10 | trial → convert |
| **Pro** | **79** | ~$25 | **400** | solo dropshipper / seller |
| **Agency** | **199** | ~$65 | **1,500** | agencies, multi-store, custom scrapes |

Launch/founder pricing (first 100–200 users): **50% off for 3 months**, or **annual =
2 months free** (Pro annual ≈ 790 TND, Agency ≈ 1,990 TND). Founder rate is a great way
to seed testimonials while the product is still maturing.

> These raise the code's current placeholders (Pro 29 TND / Agency 79 TND). Reason:
> the media buyer + money-ranked MENA data is worth well above 29 TND, and 29 TND
> leaves little room for the AI COGS once usage grows. If adoption is the priority
> over revenue early on, launch Pro at **49 TND** and step to 79 after traction.

## 4. Margin math (why these numbers work)

Per COSTS.md, an AI action costs ~1.2¢ (chat) to ~2¢ (generation) on Sonnet 4.6 + caching.

| Tier | Price | Credits | Worst-case AI COGS | Realistic COGS* | Gross margin (realistic) |
|---|---|---|---|---|---|
| Free | $0 | 10 | ~$0.20 | ~$0.10 | (loss leader — cap tight) |
| Pro | ~$25 | 400 | ~$8 (all gens) | ~$3 | **~88%** |
| Agency | ~$65 | 1,500 | ~$30 (all gens) | ~$10 | **~85%** |

\*Most users use <half their credits, and chat (cheaper) dominates over generations.
Search/Brand Spy/ingestion infra is ~free at current scale (COSTS.md §6). Subtract
payment-processor fees (~2–3% Konnect/Flouci) and margins stay high.

**Guardrails to keep it safe:**
- Meter credits per user (enforce the monthly cap) — not built yet, **required before
  launch** so a heavy Agency user can't run negative.
- Offer **credit top-ups / overage** (e.g. +200 credits for 20 TND) instead of raising
  base prices — captures whales, protects margin.
- Turn on **prompt caching** (COSTS.md §4) before charging — it's what makes the ~1.2¢
  chat cost real. Without it, halve the margins above.

## 5. Go-to-market tactics

- **Free tier is the funnel**, not charity: enough to feel the "wow" (see real MENA
  winners + a taste of the media buyer), capped so serious use requires Pro.
- **Founder pricing** for early adopters → testimonials + word of mouth in TN/MA/DZ
  dropshipping communities (Facebook groups, Discord).
- **Annual = 2 months free** to pull cash forward and cut churn.
- **Local trust:** price in TND, pay with Konnect/Flouci/e-DINAR/bank card — a big edge
  over global tools that only take international cards.
- **No true local competitor** at this feature set → we're the category default for MENA,
  not a discount clone. Don't race global tools to the bottom; win on relevance + AI.

## 6. Price ladder — how pricing moves as we ship features

Adjust tiers as these land (append to §7 when done):

| Upcoming feature | Pricing move |
|---|---|
| **Live Meta launching** (media buyer executes campaigns) | Premium add-on or a new top tier (~299–399 TND) — this is a big value jump; charge for it. |
| TikTok ads + more countries | justifies the Pro→79 step, or a higher Agency. |
| Team seats / collaboration | per-seat add-on on Agency. |
| Winning-product alerts / watchlists | Pro perk (retention), or Agency for volume. |
| Bigger AI usage (heavier media-buyer use) | raise credit allotments *and* verify COGS in COSTS.md first. |

Rule: **every feature that adds real value → either raises a tier's price or moves it
up a tier; every feature that adds real cost → re-check COSTS.md before setting limits.**

## 7. Decisions & change log

| Date | Change | Rationale |
|---|---|---|
| 2026-06-29 | Baseline strategy set: Free / Pro ~79 TND / Agency ~199 TND; 10 / 400 / 1,500 AI credits. Credits = the metered AI lever; search/brand-spy unlimited on paid. | Grounded in COSTS.md (~1–2¢/credit) + MENA value-based positioning. |
| _pending_ | Sync `payments.py` `/plans` + `konnect.PLAN_PRICES` to final numbers (currently 29/79 TND, 5/50/200 credits). | Code still holds placeholders. |
| _pending_ | Build per-user **credit metering + enforcement** before launch. | Protects margin (§4). |
| _next_ | _e.g. add live-Meta tier / launch founder pricing / raise Pro to 79_ | _fill in_ |
