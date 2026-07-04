"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import {
  ScanSearch, Loader2, Globe, Sparkles, Target, Tag, Quote,
  Megaphone, Search, BadgePercent, CheckCircle2,
} from "lucide-react";
import { authFetch, apiError, errMessage } from "@/lib/api";
import { useUsage } from "@/components/UsageProvider";
import { PageHeader } from "@/components/PageHeader";

const BRAND_INTEL_KEY = "adspy_brand_intel"; // read by the Media Buyer page

interface Intel {
  brand_name: string;
  one_liner: string;
  niche: string;
  products: { name: string; price: string | null }[];
  target_audience: string;
  price_positioning: string;
  offers_and_hooks: string[];
  usp: string[];
  tone_of_voice: string;
  ad_angles: string[];
  spy_search_terms: string[];
  confidence: "high" | "medium" | "low";
  source_url: string;
}

/** Compact plain-text version stored for the Media Buyer's context. */
function toSummary(d: Intel): string {
  return [
    `Brand: ${d.brand_name} (${d.source_url})`,
    `What: ${d.one_liner}`,
    `Niche: ${d.niche} · Positioning: ${d.price_positioning}`,
    d.products.length
      ? `Products: ${d.products.map((p) => p.name + (p.price ? ` (${p.price})` : "")).join("; ")}`
      : "",
    `Audience: ${d.target_audience}`,
    d.usp.length ? `USPs: ${d.usp.join(" · ")}` : "",
    d.offers_and_hooks.length ? `Offers: ${d.offers_and_hooks.join(" · ")}` : "",
    `Tone: ${d.tone_of_voice}`,
  ]
    .filter(Boolean)
    .join("\n");
}

const CONFIDENCE_STYLE: Record<string, string> = {
  high: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  low: "bg-red-100 text-red-600",
};

export default function IntelPage() {
  const { getToken } = useAuth();
  const { refresh: refreshUsage } = useUsage();
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [outOfCredits, setOutOfCredits] = useState(false);
  const [data, setData] = useState<Intel | null>(null);
  const [sentToBuyer, setSentToBuyer] = useState(false);

  const analyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || loading) return;
    setLoading(true);
    setError("");
    setOutOfCredits(false);
    setData(null);
    setSentToBuyer(false);
    try {
      const res = await authFetch(getToken, "/api/ai/analyze-website", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      if (res.status === 402) setOutOfCredits(true);
      if (!res.ok) throw new Error(await apiError(res));
      setData(await res.json());
      refreshUsage();
    } catch (err) {
      setError(errMessage(err, "Analysis failed"));
    } finally {
      setLoading(false);
    }
  };

  const sendToBuyer = () => {
    if (!data) return;
    try {
      localStorage.setItem(
        BRAND_INTEL_KEY,
        JSON.stringify({ brand_name: data.brand_name, summary: toSummary(data) })
      );
      setSentToBuyer(true);
    } catch {}
  };

  const spyTerm = data?.spy_search_terms?.[0];

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      <PageHeader
        icon={ScanSearch}
        gradient="from-[#ec4492] to-[#ee4454]"
        title="Website Intel"
        subtitle="Paste any store URL — yours or a competitor's — and get the brand decoded: products, audience, offers, and the exact angles to run. 1 credit per analysis."
      />

      {/* URL input */}
      <form onSubmit={analyze} className="relative mb-6 fade-up" style={{ ["--delay" as string]: "80ms" }}>
        <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="e.g. mystore.tn or competitor.com/products/serum"
          className="w-full pl-12 pr-32 py-3.5 bg-white border border-[#e6e6e7] rounded-full text-sm focus:outline-none focus:border-[#1d1d1f] transition"
        />
        <button
          type="submit"
          disabled={loading || !url.trim()}
          className="btn-holo absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 text-sm disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {loading ? "Reading the site…" : "Analyze"}
        </button>
      </form>

      {error && (
        <div className="mb-6 flex items-center justify-between gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          <p className="text-sm text-red-700">{error}</p>
          {outOfCredits && (
            <Link href="/pricing" className="btn-holo shrink-0 px-4 py-2 text-sm">
              Upgrade
            </Link>
          )}
        </div>
      )}

      {loading && (
        <div className="bg-white border border-[#e6e6e7] rounded-2xl p-10 text-center">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400 mx-auto mb-3" />
          <p className="text-sm text-[#6e6e73]">
            Fetching the page, reading the copy, decoding the brand…
          </p>
        </div>
      )}

      {data && (
        <div className="space-y-5">
          {/* Header card */}
          <div className="holo-ring rounded-2xl">
            <div className="rounded-[15px] bg-white p-6">
              <div className="flex items-start justify-between gap-3 mb-1">
                <h3 className="text-xl font-black tracking-tight text-[#1d1d1f]">{data.brand_name}</h3>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full shrink-0 ${CONFIDENCE_STYLE[data.confidence]}`}>
                  {data.confidence} confidence
                </span>
              </div>
              <p className="text-sm text-[#6e6e73] mb-3">{data.one_liner}</p>
              <div className="flex flex-wrap gap-2">
                <span className="text-xs font-semibold px-2.5 py-1 rounded-full holo-gradient text-white">
                  {data.niche}
                </span>
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 text-gray-600">
                  {data.price_positioning}
                </span>
                <a
                  href={data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium px-2.5 py-1 rounded-full border border-[#e6e6e7] text-[#6e6e73] hover:border-[#1d1d1f] transition"
                >
                  {new URL(data.source_url).hostname}
                </a>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Products */}
            {data.products.length > 0 && (
              <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
                <h4 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                  <Tag className="w-4 h-4" /> Products
                </h4>
                <ul className="space-y-1.5">
                  {data.products.map((p, i) => (
                    <li key={i} className="text-sm text-gray-700 flex justify-between gap-3">
                      <span className="truncate">{p.name}</span>
                      {p.price && <span className="text-[#6e6e73] shrink-0">{p.price}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Audience + tone */}
            <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
              <h4 className="text-sm font-bold text-[#1d1d1f] mb-2 flex items-center gap-1.5">
                <Target className="w-4 h-4" /> Who buys this
              </h4>
              <p className="text-sm text-gray-700 mb-3">{data.target_audience}</p>
              <h4 className="text-sm font-bold text-[#1d1d1f] mb-1 flex items-center gap-1.5">
                <Quote className="w-4 h-4" /> Tone
              </h4>
              <p className="text-sm text-[#6e6e73]">{data.tone_of_voice}</p>
            </div>

            {/* Offers */}
            {data.offers_and_hooks.length > 0 && (
              <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
                <h4 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                  <BadgePercent className="w-4 h-4" /> Offers & hooks on the site
                </h4>
                <ul className="space-y-1.5">
                  {data.offers_and_hooks.map((o, i) => (
                    <li key={i} className="text-sm text-gray-700 flex gap-2">
                      <span className="text-gray-300">•</span> {o}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* USPs */}
            {data.usp.length > 0 && (
              <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
                <h4 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" /> What sets them apart
                </h4>
                <ul className="space-y-1.5">
                  {data.usp.map((u, i) => (
                    <li key={i} className="text-sm text-gray-700 flex gap-2">
                      <span className="text-emerald-500">✓</span> {u}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Ad angles */}
          <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
            <h4 className="text-sm font-bold text-[#1d1d1f] mb-3 flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" /> Ad angles to run
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {data.ad_angles.map((a, i) => (
                <div key={i} className="text-sm text-gray-700 bg-[#fbfbfb] border border-[#e6e6e7] rounded-xl px-3.5 py-2.5">
                  {a}
                </div>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <button onClick={sendToBuyer} className="btn-holo px-5 py-2.5 text-sm" disabled={sentToBuyer}>
              <Megaphone className="w-4 h-4" />
              {sentToBuyer ? "Sent — open Media Buyer" : "Plan campaign with this brand"}
            </button>
            {sentToBuyer && (
              <button
                onClick={() => router.push("/mediabuyer")}
                className="px-5 py-2.5 text-sm font-semibold rounded-full border border-[#e6e6e7] hover:border-[#1d1d1f] transition"
              >
                Open Media Buyer →
              </button>
            )}
            {spyTerm && (
              <button
                onClick={() => router.push(`/search?q=${encodeURIComponent(spyTerm)}`)}
                className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-semibold rounded-full border border-[#e6e6e7] hover:border-[#1d1d1f] transition"
              >
                <Search className="w-4 h-4" /> Spy similar winning ads
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
