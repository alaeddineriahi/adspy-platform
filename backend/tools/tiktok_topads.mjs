/**
 * TikTok Creative Center — Top Ads fetcher.
 *
 * The creative_radar_api signs every request in the page's JS (user-sign /
 * timestamp headers); raw HTTP gets `40101 no permission`. So we do what the
 * FB pipeline does philosophically — let the real client do the auth: load
 * the Top Ads page per country in a headless browser and intercept the JSON
 * the page fetches for itself. One navigation yields ~2 list pages (~40 ads).
 *
 * Usage:
 *   node tiktok_topads.mjs --countries US,FR,SA --period 30 --limit 40
 * Output (stdout, single JSON object):
 *   {"countries": {"US": [material, ...]}, "errors": ["..."]}
 * Exit code 0 even on partial failure — the Python side decides severity.
 *
 * Deps: `npm install` in this directory (playwright-core only). Uses the
 * OS-installed Edge/Chrome via channel, so no browser download is needed.
 */

import { chromium } from "playwright-core";

const arg = (name, dflt) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : dflt;
};

const COUNTRIES = arg("countries", "US").split(",").map((c) => c.trim().toUpperCase()).filter(Boolean);
const PERIOD = arg("period", "30");
const LIMIT = Number(arg("limit", "40"));
const CHANNELS = [arg("channel", ""), "msedge", "chrome", ""].filter((c, i, a) => a.indexOf(c) === i);

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0";

async function launch() {
  let lastErr;
  for (const channel of CHANNELS) {
    try {
      return await chromium.launch(channel ? { channel, headless: true } : { headless: true });
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

async function collectCountry(page, country) {
  const byId = new Map();
  const handler = async (resp) => {
    if (!resp.url().includes("top_ads/v2/list") || resp.status() !== 200) return;
    try {
      const j = await resp.json();
      if (j.code === 0 && Array.isArray(j?.data?.materials)) {
        const cc = new URL(resp.url()).searchParams.get("country_code");
        if (cc && cc !== country) return; // stale response from the previous region
        for (const m of j.data.materials) if (m?.id) byId.set(m.id, m);
      }
    } catch {}
  };
  page.on("response", handler);
  try {
    await page.goto(
      `https://ads.tiktok.com/business/creativecenter/inspiration/topads/pc/en?region=${country}&period=${PERIOD}`,
      { waitUntil: "domcontentloaded", timeout: 45000 }
    );
    // The page fires its list requests after hydration; poll instead of a
    // fixed sleep so fast loads don't waste time and slow ones still land.
    for (let waited = 0; waited < 20000 && byId.size < Math.min(LIMIT, 35); waited += 1000) {
      await page.waitForTimeout(1000);
    }
  } finally {
    page.off("response", handler);
  }
  return [...byId.values()].slice(0, LIMIT);
}

const out = { countries: {}, errors: [] };
let browser;
try {
  browser = await launch();
  const ctx = await browser.newContext({
    userAgent: UA,
    locale: "en-US",
    viewport: { width: 1366, height: 900 },
  });
  // Headless Chromium exposes navigator.webdriver; the Creative Center
  // rejects such sessions at the HTTP layer (ERR_HTTP_RESPONSE_CODE_FAILURE).
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
  });
  const page = await ctx.newPage();
  for (const country of COUNTRIES) {
    try {
      const mats = await collectCountry(page, country);
      out.countries[country] = mats;
      if (!mats.length) out.errors.push(`${country}: 0 materials (region unsupported or blocked)`);
    } catch (e) {
      out.errors.push(`${country}: ${String(e).slice(0, 200)}`);
    }
  }
} catch (e) {
  out.errors.push(`launch: ${String(e).slice(0, 300)}`);
} finally {
  try { await browser?.close(); } catch {}
}

process.stdout.write(JSON.stringify(out));
