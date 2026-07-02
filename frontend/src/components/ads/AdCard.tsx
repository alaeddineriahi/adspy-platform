"use client";

import { Ad } from "@/types";
import { Bookmark, ExternalLink, Clock, Globe, ImageOff, Layers, TrendingUp, Megaphone } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useSaved } from "@/components/SavedProvider";

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
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition group">
      {/* Media preview */}
      <div className="aspect-video bg-gray-100 relative flex items-center justify-center">
        {thumb && imgOk ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumb}
            alt={ad.advertiser_name}
            className="w-full h-full object-cover"
            onError={() => setImgOk(false)}
          />
        ) : (
          <ImageOff className="w-8 h-8 text-gray-300" />
        )}
        <span
          className={`absolute top-3 left-3 px-2 py-1 rounded-md text-xs font-medium ${
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
          className={`absolute top-3 right-3 p-2 rounded-lg transition ${
            saved
              ? "bg-gray-900 text-white opacity-100"
              : "bg-white/90 text-gray-600 opacity-0 group-hover:opacity-100 hover:bg-white"
          }`}
        >
          <Bookmark className={`w-4 h-4 ${saved ? "fill-current" : ""}`} />
        </button>
        {typeof ad.performance_score === "number" && (
          <span
            className="absolute bottom-3 left-3 flex items-center gap-1 px-2 py-1 rounded-md text-xs font-semibold bg-emerald-500/90 text-white"
            title="Money score (0–100): scaling + longevity + commerce"
          >
            <TrendingUp className="w-3 h-3" />
            {Math.round(ad.performance_score)}
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
          className="flex-1 text-center py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
        >
          View details
        </Link>
        <Link
          href={`/mediabuyer?ad=${ad.id || ad.ad_id}`}
          title="Plan a campaign with the media buyer"
          className="flex items-center justify-center p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <Megaphone className="w-4 h-4 text-gray-600" />
        </Link>
        {ad.landing_page && (
          <a
            href={ad.landing_page}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <ExternalLink className="w-4 h-4 text-gray-600" />
          </a>
        )}
      </div>
    </div>
  );
}
