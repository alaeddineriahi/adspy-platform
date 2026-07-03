"use client";

import { Ad } from "@/types";
import { Bookmark, ExternalLink, Clock, Globe, Layers, TrendingUp, Megaphone, Play, Flame, Gem, CircleDollarSign } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useSaved } from "@/components/SavedProvider";

// Deterministic gradient pair per advertiser so the placeholder looks branded,
// not broken — same brand always gets the same colors.
const GRADIENTS: [string, string][] = [
  ["#3e86c6", "#a666aa"],
  ["#a666aa", "#ec4492"],
  ["#ec4492", "#ee4454"],
  ["#ee4454", "#f05427"],
  ["#f05427", "#3e86c6"],
  ["#3e86c6", "#ec4492"],
];

/** "$4.2k" style compact money formatting for spend estimates. */
export function fmtUsd(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(1).replace(/\.0$/, "")}k`;
  return `$${v}`;
}

function BrandPlaceholder({ name, format }: { name: string; format?: string }) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) | 0;
  const [from, to] = GRADIENTS[Math.abs(hash) % GRADIENTS.length];
  return (
    <div
      className="w-full h-full flex flex-col items-center justify-center gap-2"
      style={{ background: `linear-gradient(135deg, ${from}26, ${to}40)` }}
    >
      <span
        className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black text-white shadow-sm"
        style={{ background: `linear-gradient(135deg, ${from}, ${to})` }}
      >
        {format === "video" ? <Play className="w-6 h-6 fill-current" /> : name.charAt(0).toUpperCase()}
      </span>
      <span className="text-xs font-semibold text-[#1d1d1f]/60 max-w-[80%] truncate">{name}</span>
    </div>
  );
}

export function AdCard({ ad }: { ad: Ad }) {
  const platformColors: Record<string, string> = {
    meta: "bg-blue-100 text-blue-700",
    tiktok: "bg-gray-900 text-white",
    google: "bg-green-100 text-green-700",
  };

  const thumb = ad.thumbnail || ad.media_urls?.[0];
  const [imgOk, setImgOk] = useState(true);

  const savedId = ad.id || ad.ad_id;
  const { isSaved, toggle } = useSaved();
  const saved = isSaved(savedId);

  return (
    <div className="bg-white rounded-2xl border border-[#e6e6e7] overflow-hidden hover:shadow-lg hover:shadow-gray-200/70 hover:-translate-y-0.5 transition-all duration-200 group">
      {/* Media preview */}
      <div className="aspect-video bg-gray-100 relative flex items-center justify-center overflow-hidden">
        {thumb && imgOk ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumb}
            alt={ad.advertiser_name}
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
            onError={() => setImgOk(false)}
          />
        ) : (
          <BrandPlaceholder name={ad.advertiser_name || "Ad"} format={ad.ad_format} />
        )}
        <span
          className={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold ${
            platformColors[ad.platform] ?? "bg-gray-100 text-gray-700"
          }`}
        >
          {ad.platform === "meta" ? "Meta" : ad.platform === "tiktok" ? "TikTok" : ad.platform}
        </span>
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            toggle(savedId);
          }}
          title={saved ? "Remove from saved" : "Save to swipe file"}
          className={`absolute top-3 right-3 p-2 rounded-full transition ${
            saved
              ? "bg-[#1d1d1f] text-white opacity-100"
              : "bg-white/90 text-gray-600 opacity-0 group-hover:opacity-100 hover:bg-white"
          }`}
        >
          <Bookmark className={`w-4 h-4 ${saved ? "fill-current" : ""}`} />
        </button>
        {typeof (ad.heat ?? ad.performance_score) === "number" && (
          <span
            className="absolute bottom-3 left-3 flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold holo-gradient text-white shadow-sm"
            title="Money heat (0–100): scaling velocity + commerce, weighted to NOW"
          >
            <TrendingUp className="w-3 h-3" />
            {Math.round((ad.heat ?? ad.performance_score)!)}
          </span>
        )}
        {ad.momentum === "hot" && (
          <span className="absolute bottom-3 right-3 flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold text-white shadow-sm bg-gradient-to-r from-orange-500 to-red-500">
            <Flame className="w-3 h-3 fill-current" /> Scaling fast
          </span>
        )}
        {ad.momentum === "proven" && (
          <span className="absolute bottom-3 right-3 flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold text-white shadow-sm bg-gradient-to-r from-violet-600 to-indigo-500">
            <Gem className="w-3 h-3" /> Proven winner
          </span>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-900 truncate">
            {ad.advertiser_name}
          </span>
          <span className="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-600">
            {ad.ad_format}
          </span>
        </div>
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{ad.copy_text}</p>
        {/* Why-this-wins insight line */}
        {ad.momentum === "hot" && (
          <p className="text-xs font-medium text-orange-600 mb-2">
            {ad.variant_count} variants in {ad.days_running}d — budget pouring in right now
          </p>
        )}
        {ad.momentum === "proven" && (
          <p className="text-xs font-medium text-violet-600 mb-2">
            {ad.days_running}d alive & still active — validated evergreen
          </p>
        )}
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1" title="Days the creative has stayed live">
            <Clock className="w-3 h-3" />
            {ad.days_running}d
          </span>
          {typeof ad.variant_count === "number" && ad.variant_count > 1 && (
            <span className="flex items-center gap-1 text-emerald-600" title="Creative variants running (scaling = budget)">
              <Layers className="w-3 h-3" />
              {ad.variant_count}× scaling
            </span>
          )}
          {typeof ad.est_spend_min_usd === "number" && ad.est_spend_min_usd > 0 && (
            <span
              className="flex items-center gap-1 text-amber-600"
              title={
                ad.spend_basis === "reach"
                  ? `Estimated from REAL EU reach data (${ad.eu_total_reach?.toLocaleString()} people reached): ${fmtUsd(ad.est_spend_min_usd)}–${fmtUsd(ad.est_spend_max_usd!)}`
                  : `Estimated spend ${fmtUsd(ad.est_spend_min_usd)}–${fmtUsd(ad.est_spend_max_usd!)} (scaling × duration heuristic)`
              }
            >
              <CircleDollarSign className="w-3 h-3" />
              {fmtUsd(ad.est_spend_min_usd)}+{ad.spend_basis === "reach" ? " ✓" : ""}
            </span>
          )}
          <span className="flex items-center gap-1 ml-auto">
            <Globe className="w-3 h-3" />
            {ad.country}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-2">
        <Link
          href={`/ad/${ad.id || ad.ad_id}`}
          className="flex-1 text-center py-2 text-sm font-semibold bg-[#1d1d1f] text-white rounded-full hover:bg-black transition"
        >
          View details
        </Link>
        <Link
          href={`/mediabuyer?ad=${ad.id || ad.ad_id}`}
          title="Plan a campaign with the media buyer"
          className="flex items-center justify-center w-9 h-9 border border-[#e6e6e7] rounded-full hover:border-[#1d1d1f] transition"
        >
          <Megaphone className="w-4 h-4 text-gray-600" />
        </Link>
        {ad.landing_page && (
          <a
            href={ad.landing_page}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center w-9 h-9 border border-[#e6e6e7] rounded-full hover:border-[#1d1d1f] transition"
          >
            <ExternalLink className="w-4 h-4 text-gray-600" />
          </a>
        )}
      </div>
    </div>
  );
}
