"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  ArrowLeft, Bookmark, ExternalLink, Clock, Globe, Zap,
  Copy, CheckCheck, Loader2, Calendar, Package
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { authFetch, apiError, errMessage, API_URL } from "@/lib/api";
import { useUsage } from "@/components/UsageProvider";
import { fmtUsd } from "@/components/ads/AdCard";
import { Ad } from "@/types";

interface ScriptHook {
  type: string;
  text: string;
}
interface ScriptResult {
  error?: string;
  out_of_credits?: boolean;
  parse_error?: boolean;
  analysis?: string;
  hooks?: ScriptHook[];
  script?: { full_script?: string } & Record<string, unknown>;
}

export default function AdDetailPage() {
  const { id } = useParams();
  const { getToken } = useAuth();
  const { refresh: refreshUsage } = useUsage();
  const [ad, setAd] = useState<Ad | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [script, setScript] = useState<ScriptResult | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/creatives/${id}`)
      // A 404 body ({detail: "Ad not found"}) is truthy — passing it to setAd
      // renders an empty husk of a page instead of the not-found state.
      .then((r) => (r.ok ? r.json() : null))
      .then(setAd)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  const copyText = () => {
    if (ad?.copy_text) {
      navigator.clipboard.writeText(ad.copy_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const generateScript = async () => {
    setGenerating(true);
    try {
      const res = await authFetch(getToken, "/api/ai/generate-script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ad_id: id, language: ad?.language || "en" }),
      });
      if (!res.ok) {
        setScript({ error: await apiError(res), out_of_credits: res.status === 402 });
        return;
      }
      setScript(await res.json());
      refreshUsage();
    } catch (err) {
      setScript({ error: errMessage(err, "Generation failed") });
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!ad) {
    return (
      <div className="p-8 text-center text-gray-500">
        <p>Ad not found</p>
        <Link href="/search" className="text-blue-600 text-sm mt-2 inline-block">
          Back to search
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      <Link href="/search" className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to search
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Left: Media */}
        <div className="lg:col-span-3 fade-up" style={{ ["--delay" as string]: "0ms" }}>
          <div className="bg-gray-100 rounded-xl overflow-hidden aspect-video mb-4">
            {ad.media_urls?.[0] ? (
              ad.ad_format === "video" ? (
                <video src={ad.media_urls[0]} controls className="w-full h-full object-contain" />
              ) : (
                <img src={ad.media_urls[0]} alt={ad.advertiser_name} className="w-full h-full object-contain" />
              )
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">No preview</div>
            )}
          </div>

          {/* Thumbnails */}
          {ad.media_urls && ad.media_urls.length > 1 && (
            <div className="flex gap-2 overflow-x-auto">
              {ad.media_urls.map((url, i) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={i} src={url} alt={`${ad.advertiser_name} creative ${i + 1}`} className="w-20 h-20 rounded-xl object-cover border-2 border-transparent hover:border-[#1d1d1f] cursor-pointer" />
              ))}
            </div>
          )}
        </div>

        {/* Right: Info */}
        <div className="lg:col-span-2 fade-up" style={{ ["--delay" as string]: "100ms" }}>
          <div className="flex items-center gap-3 mb-4">
            <span className={`px-2.5 py-1 rounded-md text-xs font-medium ${
              ad.platform === "meta" ? "bg-blue-100 text-blue-700" : "bg-gray-900 text-white"
            }`}>
              {ad.platform === "meta" ? "Meta" : "TikTok"}
            </span>
            <span className="px-2.5 py-1 bg-gray-100 rounded-md text-xs text-gray-600">{ad.ad_format}</span>
            {ad.is_active && (
              <span className="px-2.5 py-1 bg-green-100 text-green-700 rounded-md text-xs">Active</span>
            )}
          </div>

          <h1 className="text-xl font-black tracking-tight text-[#1d1d1f] mb-1">{ad.advertiser_name}</h1>

          <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
            <span className="flex items-center gap-1"><Globe className="w-4 h-4" />{ad.country}</span>
            <span className="flex items-center gap-1"><Clock className="w-4 h-4" />{ad.days_running}d running</span>
            <span className="flex items-center gap-1"><Calendar className="w-4 h-4" />{ad.first_seen?.slice(0, 10)}</span>
          </div>

          {/* Estimated spend */}
          {typeof ad.est_spend_min_usd === "number" && ad.est_spend_min_usd > 0 && (
            <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 mb-6">
              <p className="text-sm font-semibold text-amber-900">
                💰 Est. total spend: {fmtUsd(ad.est_spend_min_usd)} – {fmtUsd(ad.est_spend_max_usd!)}
                {ad.spend_basis === "reach" && (
                  <span className="ml-1.5 text-[11px] font-bold text-emerald-700 bg-emerald-100 px-1.5 py-0.5 rounded">
                    ✓ real reach data
                  </span>
                )}
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                {ad.spend_basis === "reach"
                  ? `Based on ${ad.eu_total_reach?.toLocaleString()} people actually reached (EU transparency data) × market CPM.`
                  : `Estimate from ${ad.variant_count ?? 1} creative variants × ${ad.days_running}d runtime × market budgets. Meta doesn't publish exact spend for commercial ads — nobody has it.`}
              </p>
            </div>
          )}

          {/* Ad copy */}
          <div className="bg-gray-50 rounded-xl p-4 mb-4 relative group">
            <p className="text-sm text-gray-800 whitespace-pre-wrap">{ad.copy_text}</p>
            <button
              onClick={copyText}
              className="absolute top-3 right-3 p-1.5 bg-white rounded-md border border-gray-200 opacity-0 group-hover:opacity-100 transition"
            >
              {copied ? <CheckCheck className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4 text-gray-500" />}
            </button>
          </div>

          {ad.cta_text && (
            <p className="text-sm mb-4"><span className="text-gray-500">CTA:</span> <span className="font-medium">{ad.cta_text}</span></p>
          )}

          {/* Actions */}
          <div className="flex flex-col gap-3">
            <Link
              href={`/dossier/${id}`}
              className="btn-holo w-full py-3 text-sm text-center"
            >
              <Package className="w-4 h-4" />
              Full product dossier — margin, gaps, sourcing
            </Link>
            <button
              onClick={generateScript}
              disabled={generating}
              className="w-full py-3 text-sm flex items-center justify-center gap-2 border border-[#1d1d1f] rounded-full font-semibold hover:bg-gray-50 transition disabled:opacity-50"
            >
              {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              Generate AI script
            </button>

            <div className="flex gap-3">
              <button className="flex-1 flex items-center justify-center gap-2 py-2.5 border border-gray-300 rounded-xl text-sm hover:bg-gray-50">
                <Bookmark className="w-4 h-4" /> Save
              </button>
              {ad.landing_page && (
                <a
                  href={ad.landing_page}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 border border-gray-300 rounded-xl text-sm hover:bg-gray-50"
                >
                  <ExternalLink className="w-4 h-4" /> Landing page
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI Script output */}
      {script && !script.parse_error && (
        <div className="mt-10 bg-white border border-[#e6e6e7] rounded-2xl p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-blue-600" /> AI-generated script
          </h3>

          {script.error && (
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm text-red-600">{script.error}</p>
              {script.out_of_credits && (
                <Link
                  href="/pricing"
                  className="btn-holo shrink-0 px-4 py-2 text-sm"
                >
                  Upgrade
                </Link>
              )}
            </div>
          )}

          {script.analysis && (
            <div className="bg-blue-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-blue-800"><strong>Why this ad works:</strong> {script.analysis}</p>
            </div>
          )}

          {/* Hooks */}
          {script.hooks && (
            <div className="mb-6">
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Hook variations</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {script.hooks.map((hook, i) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-4">
                    <span className="text-xs font-medium text-gray-500 uppercase mb-2 block">
                      {hook.type}
                    </span>
                    <p className="text-sm text-gray-900">{hook.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Full script */}
          {script.script && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-3">Full script</h4>
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap">
                {script.script.full_script || JSON.stringify(script.script, null, 2)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
