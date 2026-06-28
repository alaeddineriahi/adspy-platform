"use client";

import { Ad } from "@/types";
import { Bookmark, ExternalLink, Clock, Globe } from "lucide-react";
import Link from "next/link";

export function AdCard({ ad }: { ad: Ad }) {
  const platformColors = {
    meta: "bg-blue-100 text-blue-700",
    tiktok: "bg-gray-900 text-white",
    google: "bg-green-100 text-green-700",
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition group">
      {/* Media preview */}
      <div className="aspect-video bg-gray-100 relative">
        {ad.media_urls[0] && (
          <img
            src={ad.media_urls[0]}
            alt={ad.advertiser_name}
            className="w-full h-full object-cover"
          />
        )}
        <span className={`absolute top-3 left-3 px-2 py-1 rounded-md text-xs font-medium ${platformColors[ad.platform]}`}>
          {ad.platform === "meta" ? "Meta" : "TikTok"}
        </span>
        <button className="absolute top-3 right-3 p-2 bg-white/90 rounded-lg opacity-0 group-hover:opacity-100 transition hover:bg-white">
          <Bookmark className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-900 truncate">{ad.advertiser_name}</span>
          <span className="text-xs px-2 py-0.5 bg-gray-100 rounded text-gray-600">{ad.ad_format}</span>
        </div>
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{ad.copy_text}</p>
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {ad.days_running}d running
          </span>
          <span className="flex items-center gap-1">
            <Globe className="w-3 h-3" />
            {ad.country}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-2">
        <Link
          href={`/ad/${ad.id}`}
          className="flex-1 text-center py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800"
        >
          View details
        </Link>
        <a
          href={ad.landing_page}
          target="_blank"
          rel="noopener noreferrer"
          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <ExternalLink className="w-4 h-4 text-gray-600" />
        </a>
      </div>
    </div>
  );
}
