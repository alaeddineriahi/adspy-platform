"use client";

import { useState } from "react";
import { Search, Filter, SlidersHorizontal } from "lucide-react";

type Platform = "all" | "meta" | "tiktok";
type AdFormat = "all" | "image" | "video" | "carousel";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState<Platform>("all");
  const [format, setFormat] = useState<AdFormat>("all");
  const [country, setCountry] = useState("all");

  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">Search ads</h2>

      {/* Search bar */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by keyword, brand, or domain..."
          className="w-full pl-12 pr-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-8">
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value as Platform)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">All platforms</option>
          <option value="meta">Meta (FB + IG)</option>
          <option value="tiktok">TikTok</option>
        </select>

        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as AdFormat)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">All formats</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="carousel">Carousel</option>
        </select>

        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg text-sm bg-white"
        >
          <option value="all">All countries</option>
          <option value="TN">Tunisia</option>
          <option value="DZ">Algeria</option>
          <option value="MA">Morocco</option>
          <option value="EG">Egypt</option>
          <option value="SA">Saudi Arabia</option>
          <option value="AE">UAE</option>
        </select>

        <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">
          <SlidersHorizontal className="w-4 h-4" />
          More filters
        </button>
      </div>

      {/* Results placeholder */}
      <div className="text-center py-20 text-gray-400">
        <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p className="text-lg">Search for ads to get started</p>
        <p className="text-sm mt-2">Try &quot;e-commerce Tunisia&quot; or &quot;fashion UAE&quot;</p>
      </div>
    </div>
  );
}
