"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import {
  ArrowLeft, Package, Loader2, Flame, Layers, Clock, CircleDollarSign, Radio,
  TrendingUp, Target, ShoppingCart, ExternalLink, Megaphone, Zap, AlertTriangle,
  Sparkles, Lock,
} from "lucide-react";
import { authFetch, apiError, errMessage, API_URL } from "@/lib/api";
import { useUsage } from "@/components/UsageProvider";
import { fmtUsd } from "@/components/ads/AdCard";
import { Ad } from "@/types";

interface Dossier {
  product: { name: string; category?: string; what_it_is?: string; target_audience?: string };
  proof: {
    heat?: number; momentum?: string; variant_count?: number; days_running?: number;
    est_spend_min_usd?: number; est_spend_max_usd?: number; brand_live_ads?: number;
  };
  price_local?: { amount: number; currency: string } | null;
  margin?: {
    sell_price_usd: number; supply_cost_usd_min: number; supply_cost_usd_max: number;
    est_fees_usd: number; est_profit_usd: number; margin_pct: number;
  } | null;
  pricing_hint?: {
    supply_cost_usd_min: number; supply_cost_usd_max: number;
    suggested_sell_usd_min: number; suggested_sell_usd_max: number;
  } | null;
  market_map: {
    presence: Record<string, number>; open_mena: string[]; open_global: string[];
    saturation: string; saturation_meaning: string; brand_count: number;
    verify_urls?: Record<string, string>;
    live_counts?: Record<string, number>;
  };
  competitors: { advertiser_name: string; advertiser_id?: string; total_variants: number; markets: string[]; max_heat: number }[];
  funnel?: {
    store_platform?: string | null;
    offer?: string | null;
    displayed_price?: string | null;
    bundles_upsells?: string[];
    cod_available?: boolean | null;
    trust_elements?: string[];
    weaknesses?: string[];
    takeaway?: string;
    source_url?: string;
  } | null;
  angles: string[];
  risk_notes?: string;
  verdict_line?: string;
  sourcing: {
    search_term?: string;
    aliexpress_url?: string;
    alibaba_url?: string;
    made_in_china_url?: string;
    local?: {
      feasible: boolean;
      is_supplement: boolean;
      note?: string;
      tunisia_sources: { name: string; note?: string; url?: string }[];
    };
  };
  keywords?: { fr?: string; ar?: string; en?: string };
  cached?: boolean;
  credits_charged?: number;
}

const SAT_STYLES: Record<string, { label: string; cls: string }> = {
  wide_open: { label: "Wide open", cls: "from-emerald-500 to-teal-500" },
  heating_up: { label: "Heating up", cls: "from-amber-500 to-orange-500" },
  crowded: { label: "Crowded", cls: "from-orange-500 to-red-500" },
  saturated: { label: "Saturated", cls: "from-red-500 to-rose-600" },
};

export default function DossierPage() {
  const { id } = useParams();
  const { getToken } = useAuth();
  const { refresh: refreshUsage } = useUsage();
  const [ad, setAd] = useState<Ad | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [outOfCredits, setOutOfCredits] = useState(false);

  const cacheKey = `adspy_dossier_v6_${id}`; // v6: live Ad Library counts on open markets

  useEffect(() => {
    if (!id) return;
    fetch(`${API_URL}/api/creatives/${id}`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setAd)
      .catch(() => {});
    try {
      const cached = localStorage.getItem(cacheKey);
      if (cached) setDossier(JSON.parse(cached));
    } catch {}
  }, [id, cacheKey]);

  const generate = useCallback(async () => {
    setLoading(true);
    setError("");
    setOutOfCredits(false);
    try {
      const res = await authFetch(getToken, "/api/ai/dossier", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ad_id: id }),
      });
      if (!res.ok) {
        setOutOfCredits(res.status === 402);
        setError(await apiError(res));
        return;
      }
      const data: Dossier = await res.json();
      setDossier(data);
      try { localStorage.setItem(cacheKey, JSON.stringify(data)); } catch {}
      refreshUsage();
    } catch (e) {
      setError(errMessage(e, "Dossier failed — try again."));
    } finally {
      setLoading(false);
    }
  }, [getToken, id, cacheKey, refreshUsage]);

  const sat = dossier ? SAT_STYLES[dossier.market_map.saturation] ?? SAT_STYLES.heating_up : null;

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      <Link href={`/creative/${id}`} className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-4">
        <ArrowLeft className="w-4 h-4" /> Back to ad
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-8 fade-up" style={{ ["--delay" as string]: "0ms" }}>
        <div className="flex items-start gap-3.5">
          <span className="w-11 h-11 shrink-0 rounded-xl flex items-center justify-center text-white bg-gradient-to-br from-[#f05427] to-[#ec4492] shadow-sm">
            <Package className="w-5 h-5" />
          </span>
          <div>
            <h2 className="text-2xl font-black tracking-tight text-[#1d1d1f]">
              {dossier ? dossier.product.name : "Product Dossier"}
            </h2>
            <p className="text-sm text-[#6e6e73] mt-0.5 max-w-xl">
              {dossier
                ? `${dossier.product.category ?? ""} — sold by ${ad?.advertiser_name ?? "…"}`
                : "The complete business in a box: what it is, the margin, who's on it, which markets are still open, and where to source it."}
            </p>
          </div>
        </div>
        {ad?.thumbnail && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={ad.thumbnail} alt="" className="w-20 h-20 rounded-2xl object-cover border border-[#e6e6e7] hidden sm:block fade-up" style={{ ["--delay" as string]: "120ms" }} />
        )}
      </div>

      {!dossier && (
        <div className="bg-white border border-[#e6e6e7] rounded-2xl p-8 text-center fade-up" style={{ ["--delay" as string]: "100ms" }}>
          <Sparkles className="w-10 h-10 mx-auto mb-3 text-[#ec4492]" />
          <p className="text-sm text-gray-600 max-w-md mx-auto mb-5">
            One click compiles the product identity, honest margin math, competition
            saturation, the market-gap map, and supplier links for this winner.
          </p>
          <button onClick={generate} disabled={loading} className="btn-holo px-6 py-3 text-sm disabled:opacity-50">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Package className="w-4 h-4" />}
            {loading ? "Compiling the dossier…" : "Generate dossier · 2 credits (1 if recently compiled)"}
          </button>
          {error && (
            <div className="mt-4 flex items-center justify-center gap-3">
              <p className="text-sm text-red-600">{error}</p>
              {outOfCredits && (
                <Link href="/pricing" className="btn-holo px-4 py-2 text-sm"><Lock className="w-3.5 h-3.5" /> Upgrade</Link>
              )}
            </div>
          )}
        </div>
      )}

      {dossier && (
        <div className="space-y-5">
          {/* Verdict */}
          {dossier.verdict_line && (
            <div className="holo-gradient text-white rounded-2xl p-4 flex items-center gap-3 fade-up" style={{ ["--delay" as string]: "60ms" }}>
              <Target className="w-5 h-5 shrink-0" />
              <p className="text-sm font-semibold">{dossier.verdict_line}</p>
            </div>
          )}

          {/* Proof strip */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 fade-up" style={{ ["--delay" as string]: "120ms" }}>
            <Proof icon={TrendingUp} label="Heat" value={dossier.proof.heat != null ? String(Math.round(dossier.proof.heat)) : "—"} />
            <Proof icon={Layers} label="Variants" value={`${dossier.proof.variant_count ?? "—"}×`} />
            <Proof icon={Clock} label="Running" value={`${dossier.proof.days_running ?? "—"}d`} />
            <Proof icon={CircleDollarSign} label="Est. spend" value={dossier.proof.est_spend_min_usd ? `${fmtUsd(dossier.proof.est_spend_min_usd)}+` : "—"} />
            <Proof icon={Radio} label="Brand ads live" value={dossier.proof.brand_live_ads ? String(dossier.proof.brand_live_ads) : "—"} />
          </div>

          {/* What it is */}
          <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "180ms" }}>
            <h3 className="text-sm font-bold text-[#1d1d1f] mb-2">What it is</h3>
            <p className="text-sm text-gray-700">{dossier.product.what_it_is}</p>
            {dossier.product.target_audience && (
              <p className="text-xs text-gray-500 mt-2">🎯 {dossier.product.target_audience}</p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Margin math */}
            <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "240ms" }}>
              <h3 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                <CircleDollarSign className="w-4 h-4 text-amber-500" /> The margin
              </h3>
              {dossier.margin ? (
                <>
                  <p className="text-4xl font-black text-emerald-600">{dossier.margin.margin_pct}%</p>
                  <p className="text-xs text-gray-500 mb-3">est. net margin per sale</p>
                  <dl className="text-xs text-gray-600 space-y-1.5">
                    <Row k={`Sells at${dossier.price_local ? ` (${dossier.price_local.amount} ${dossier.price_local.currency})` : ""}`} v={`$${dossier.margin.sell_price_usd}`} />
                    <Row k="Supply cost (AliExpress est.)" v={`$${dossier.margin.supply_cost_usd_min}–$${dossier.margin.supply_cost_usd_max}`} />
                    <Row k="COD + shipping + returns (~18%)" v={`−$${dossier.margin.est_fees_usd}`} />
                    <Row k="Est. profit / sale" v={`$${dossier.margin.est_profit_usd}`} strong />
                  </dl>
                </>
              ) : dossier.pricing_hint ? (
                <>
                  <p className="text-sm text-gray-700 mb-3">
                    No price in the ad copy — but here&apos;s the playbook:
                  </p>
                  <dl className="text-xs text-gray-600 space-y-1.5">
                    <Row k="Supply cost (AliExpress est.)" v={`$${dossier.pricing_hint.supply_cost_usd_min}–$${dossier.pricing_hint.supply_cost_usd_max}`} />
                    <Row k="Typical COD sell price (3–4× supply)" v={`$${dossier.pricing_hint.suggested_sell_usd_min}–$${dossier.pricing_hint.suggested_sell_usd_max}`} strong />
                  </dl>
                </>
              ) : (
                <p className="text-sm text-gray-500">Couldn&apos;t establish pricing for this one.</p>
              )}
            </div>

            {/* Market gap map */}
            <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "300ms" }}>
              <h3 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                <Target className="w-4 h-4 text-blue-500" /> Market map
                {sat && (
                  <span className={`ml-auto text-[11px] font-bold text-white px-2 py-0.5 rounded-full bg-gradient-to-r ${sat.cls}`}>
                    {sat.label} · {dossier.market_map.brand_count} brand{dossier.market_map.brand_count === 1 ? "" : "s"}
                  </span>
                )}
              </h3>
              <p className="text-xs text-gray-500 mb-3">{dossier.market_map.saturation_meaning}</p>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {Object.entries(dossier.market_map.presence).map(([c, n]) => {
                  const v = dossier.market_map.verify_urls?.[c];
                  return v ? (
                    <a key={c} href={v} target="_blank" rel="noopener noreferrer"
                       className="px-2 py-1 rounded-full text-[11px] font-bold bg-gray-900 text-white hover:opacity-80 transition"
                       title={`${n} winner(s) in our catalog — click to see ALL live ads in the Ad Library`}>
                      {c} · {n} ↗
                    </a>
                  ) : (
                    <span key={c} className="px-2 py-1 rounded-full text-[11px] font-bold bg-gray-900 text-white" title={`${n} winner(s) in our catalog`}>
                      {c} · {n}
                    </span>
                  );
                })}
              </div>
              {dossier.market_map.open_mena.length > 0 && (
                <>
                  <p className="text-[11px] font-bold text-emerald-600 uppercase tracking-wide mb-1.5">
                    🎯 Open in our winners catalog — tap a market to verify live
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {dossier.market_map.open_mena.map((c) => {
                      const v = dossier.market_map.verify_urls?.[c];
                      const live = dossier.market_map.live_counts?.[c];
                      // Probed live against Meta's Ad Library at compile time:
                      // 0 = a verified first-mover claim; >0 = live sellers our
                      // sweeps hadn't indexed; undefined = probe unavailable.
                      const label =
                        live === 0 ? `${c} · 0 live ✓` : typeof live === "number" ? `${c} · ${live} live ⚠` : `${c} ↗`;
                      const cls =
                        typeof live === "number" && live > 0
                          ? "border-amber-300 text-amber-700 bg-amber-50 hover:bg-amber-100"
                          : "border-emerald-300 text-emerald-700 bg-emerald-50 hover:bg-emerald-100";
                      const tip =
                        live === 0
                          ? "Verified against the live Ad Library: ZERO active ads for this product here — first-mover territory"
                          : typeof live === "number"
                          ? `${live} live ad${live === 1 ? "" : "s"} in the Ad Library right now — not in our winners catalog yet, so none has proven itself; click to inspect`
                          : "No proven winner in our catalog here — click to check the live Ad Library yourself";
                      return v ? (
                        <a key={c} href={v} target="_blank" rel="noopener noreferrer"
                           className={`px-2 py-1 rounded-full text-[11px] font-bold border-2 border-dashed transition ${cls}`}
                           title={tip}>
                          {label}
                        </a>
                      ) : (
                        <span key={c} title={tip}
                              className={`px-2 py-1 rounded-full text-[11px] font-bold border-2 border-dashed ${cls}`}>
                          {label}
                        </span>
                      );
                    })}
                  </div>
                  <p className="text-[11px] text-gray-400 mt-2">
                    &quot;Open&quot; = no proven winner in our catalog. Markets marked <span className="font-semibold text-emerald-600">0 live ✓</span> were verified against Meta&apos;s live Ad Library when this dossier was compiled; <span className="font-semibold text-amber-600">N live ⚠</span> means ads run there but none has proven itself yet. The ↗ links open the live search.
                  </p>
                </>
              )}
              {dossier.market_map.open_global.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                  <span className="text-[11px] text-gray-400">🌍 Trend markets:</span>
                  {dossier.market_map.open_global.map((c) => {
                    const v = dossier.market_map.verify_urls?.[c];
                    return v ? (
                      <a key={c} href={v} target="_blank" rel="noopener noreferrer"
                         className="px-2 py-0.5 rounded-full text-[11px] font-semibold border border-dashed border-gray-300 text-gray-500 hover:border-gray-500 transition"
                         title="Check the live Ad Library in this trend market">
                        {c} ↗
                      </a>
                    ) : (
                      <span key={c} className="px-2 py-0.5 rounded-full text-[11px] font-semibold border border-dashed border-gray-300 text-gray-500">{c}</span>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Competitors */}
          {dossier.competitors.length > 0 && (
            <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "360ms" }}>
              <h3 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-orange-500" /> Who&apos;s running it
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {dossier.competitors.map((c) => (
                  <Link
                    key={c.advertiser_name}
                    href={c.advertiser_id ? `/brands/${c.advertiser_id}` : "#"}
                    className="flex items-center justify-between gap-2 px-3 py-2 rounded-xl border border-[#e6e6e7] hover:border-[#1d1d1f] transition text-sm"
                  >
                    <span className="font-semibold text-gray-800 truncate">{c.advertiser_name}</span>
                    <span className="text-xs text-gray-400 shrink-0">{c.total_variants}× · {c.markets.join(" ")}</span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Funnel teardown — CRO dissection of the winner's own store page */}
          {dossier.funnel && (
            <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "390ms" }}>
              <h3 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                <ExternalLink className="w-4 h-4 text-sky-500" /> Their funnel, dissected
                {dossier.funnel.store_platform && (
                  <span className="text-[11px] font-semibold text-gray-400 normal-case">· {dossier.funnel.store_platform}</span>
                )}
                {dossier.funnel.source_url && (
                  <a href={dossier.funnel.source_url} target="_blank" rel="noopener noreferrer"
                     className="ml-auto text-[11px] font-semibold text-sky-600 hover:underline">
                    visit page ↗
                  </a>
                )}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                {dossier.funnel.offer && (
                  <p><span className="text-gray-400">Offer:</span> <span className="font-medium text-gray-800">{dossier.funnel.offer}</span></p>
                )}
                {dossier.funnel.displayed_price && (
                  <p><span className="text-gray-400">Price on page:</span> <span className="font-medium text-gray-800">{dossier.funnel.displayed_price}</span></p>
                )}
                {typeof dossier.funnel.cod_available === "boolean" && (
                  <p><span className="text-gray-400">COD:</span> <span className="font-medium text-gray-800">{dossier.funnel.cod_available ? "✓ offered" : "not mentioned"}</span></p>
                )}
                {(dossier.funnel.bundles_upsells?.length ?? 0) > 0 && (
                  <p><span className="text-gray-400">Upsells:</span> <span className="font-medium text-gray-800">{dossier.funnel.bundles_upsells!.join(" · ")}</span></p>
                )}
              </div>
              {(dossier.funnel.trust_elements?.length ?? 0) > 0 && (
                <p className="text-xs text-gray-500 mt-2.5">
                  <span className="font-semibold text-gray-600">Trust they lean on:</span> {dossier.funnel.trust_elements!.join(" · ")}
                </p>
              )}
              {(dossier.funnel.weaknesses?.length ?? 0) > 0 && (
                <div className="mt-3 bg-emerald-50 border border-emerald-100 rounded-xl px-3.5 py-2.5">
                  <p className="text-[11px] font-bold text-emerald-700 uppercase tracking-wide mb-1">⚔️ Where to beat them</p>
                  <ul className="text-sm text-emerald-900 space-y-1">
                    {dossier.funnel.weaknesses!.map((w, i) => (
                      <li key={i} className="flex gap-1.5"><span>•</span> {w}</li>
                    ))}
                  </ul>
                </div>
              )}
              {dossier.funnel.takeaway && (
                <p className="text-sm font-semibold text-[#1d1d1f] mt-3">💡 {dossier.funnel.takeaway}</p>
              )}
            </div>
          )}

          {/* Angles + risk */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {dossier.angles.length > 0 && (
              <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "420ms" }}>
                <h3 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                  <Zap className="w-4 h-4 text-violet-500" /> Angles worth stealing
                </h3>
                <ul className="text-sm text-gray-700 space-y-2">
                  {dossier.angles.map((a, i) => (
                    <li key={i} className="flex gap-2"><span className="text-violet-500 font-bold">{i + 1}.</span> {a}</li>
                  ))}
                </ul>
              </div>
            )}
            {dossier.risk_notes && (
              <div className="bg-amber-50 border border-amber-100 rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "480ms" }}>
                <h3 className="text-sm font-bold text-amber-900 mb-2 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4" /> Watch out
                </h3>
                <p className="text-sm text-amber-800">{dossier.risk_notes}</p>
              </div>
            )}
          </div>

          {/* Source it */}
          <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "540ms" }}>
            <h3 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
              <ShoppingCart className="w-4 h-4 text-emerald-600" /> Source it
            </h3>

            {/* 🇹🇳 Local manufacturing — the edge China can't match */}
            {dossier.sourcing.local?.feasible && (
              <div className="mb-4 rounded-xl border border-red-100 bg-gradient-to-br from-red-50 to-white p-4">
                <p className="text-sm font-bold text-[#1d1d1f] mb-1">
                  🇹🇳 Make it in Tunisia{dossier.sourcing.local.is_supplement ? " — contract labs (façonnage)" : ""}
                </p>
                {dossier.sourcing.local.note && (
                  <p className="text-xs text-gray-600 mb-3">{dossier.sourcing.local.note}</p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {dossier.sourcing.local.tunisia_sources.map((s) => (
                    <a
                      key={s.name}
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start justify-between gap-2 px-3 py-2 rounded-lg border border-[#e6e6e7] bg-white hover:border-[#1d1d1f] transition"
                    >
                      <span className="min-w-0">
                        <span className="block text-xs font-bold text-[#1d1d1f] truncate">{s.name}</span>
                        {s.note && <span className="block text-[11px] text-gray-500">{s.note}</span>}
                      </span>
                      <ExternalLink className="w-3 h-3 text-gray-400 shrink-0 mt-1" />
                    </a>
                  ))}
                </div>
                <p className="text-[11px] text-gray-400 mt-2">
                  Local = no customs, ~1-week restock, COD-friendly cash cycle, and &quot;fabriqué en Tunisie&quot; as a trust angle. Verify MOQ &amp; certifications directly.
                </p>
              </div>
            )}

            <div className="flex flex-wrap gap-2.5">
              {dossier.sourcing.aliexpress_url && (
                <a href={dossier.sourcing.aliexpress_url} target="_blank" rel="noopener noreferrer"
                   className="flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-semibold border border-[#e6e6e7] hover:border-[#1d1d1f] transition">
                  <ShoppingCart className="w-4 h-4" /> AliExpress (test units) <ExternalLink className="w-3 h-3 text-gray-400" />
                </a>
              )}
              {dossier.sourcing.alibaba_url && (
                <a href={dossier.sourcing.alibaba_url} target="_blank" rel="noopener noreferrer"
                   className="flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-semibold border border-[#e6e6e7] hover:border-[#1d1d1f] transition">
                  <ShoppingCart className="w-4 h-4" /> Alibaba (bulk) <ExternalLink className="w-3 h-3 text-gray-400" />
                </a>
              )}
              {dossier.sourcing.made_in_china_url && (
                <a href={dossier.sourcing.made_in_china_url} target="_blank" rel="noopener noreferrer"
                   className="flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-semibold border border-[#e6e6e7] hover:border-[#1d1d1f] transition">
                  <ShoppingCart className="w-4 h-4" /> Made-in-China <ExternalLink className="w-3 h-3 text-gray-400" />
                </a>
              )}
            </div>
          </div>

          {/* Launch bar */}
          <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 fade-up" style={{ ["--delay" as string]: "600ms" }}>
            <h3 className="text-sm font-bold text-[#1d1d1f] mb-3">Launch it</h3>
            <div className="flex flex-wrap gap-2.5">
              {(dossier.keywords?.fr || dossier.keywords?.en) && (
                <Link
                  href={`/search?q=${encodeURIComponent(dossier.keywords.fr || dossier.keywords.en!)}`}
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-semibold border border-[#e6e6e7] hover:border-[#1d1d1f] transition"
                >
                  <Target className="w-4 h-4" /> Spy all similar winners
                </Link>
              )}
              <Link href={`/creative/${id}`} className="flex items-center gap-1.5 px-4 py-2.5 rounded-full text-sm font-semibold border border-[#e6e6e7] hover:border-[#1d1d1f] transition">
                <Zap className="w-4 h-4" /> Generate my ad pack
              </Link>
              <Link href={`/mediabuyer?creative=${id}`} className="btn-holo px-4 py-2.5 text-sm">
                <Megaphone className="w-4 h-4" /> Plan the campaign
              </Link>
            </div>
          </div>

          <p className="text-[11px] text-gray-400 text-center pb-4">
            {dossier.cached ? "⚡ Served from recent intelligence (1 credit). " : ""}
            Supply costs and margins are estimates (typical AliExpress pricing + ~18% COD/shipping fees) — validate with your supplier before scaling.
          </p>
        </div>
      )}
    </div>
  );
}

function Proof({ icon: Icon, label, value }: { icon: typeof Flame; label: string; value: string }) {
  return (
    <div className="bg-white border border-[#e6e6e7] rounded-2xl p-3 text-center">
      <Icon className="w-4 h-4 mx-auto mb-1 text-gray-400" />
      <p className="text-lg font-black text-[#1d1d1f]">{value}</p>
      <p className="text-[11px] text-gray-500">{label}</p>
    </div>
  );
}

function Row({ k, v, strong }: { k: string; v: string; strong?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="text-gray-500">{k}</dt>
      <dd className={strong ? "font-bold text-[#1d1d1f]" : "font-medium text-gray-700"}>{v}</dd>
    </div>
  );
}
