"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Search, Loader2, TrendingUp } from "lucide-react";
import { AdCard } from "@/components/ads/AdCard";
import { SkeletonCard } from "@/components/ads/SkeletonCard";
import { PageHeader, Stagger } from "@/components/PageHeader";
import { Ad } from "@/types";

type Platform = "all" | "meta" | "tiktok";
type AdFormat = "all" | "image" | "video" | "carousel";
type SortBy = "best_performing" | "newest" | "longest_running" | "relevance";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState<Platform>("all");
  const [format, setFormat] = useState<AdFormat>("all");
  const [country, setCountry] = useState("all");
  const [sort, setSort] = useState<SortBy>("best_performing");
  const [results, setResults] = useState<Ad[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [searched, setSearched] = useState(false);
  const [page, setPage] = useState(1);

  const doSearch = useCallback(async (p: number = 1, qOverride?: string) => {
    setLoading(true);
    setSearched(true);

    const term = qOverride ?? query;
    const params = new URLSearchParams();
    if (term) params.set("q", term);
    if (platform !== "all") params.set("platform", platform);
    if (format !== "all") params.set("format", format);
    if (country !== "all") params.set("country", country);
    params.set("sort", sort);
    params.set("page", String(p));
    params.set("limit", "20");

    try {
      const res = await fetch(`${API_URL}/api/creatives/search?${params}`);
      const data = await res.json();
      setResults(data.results || []);
      setTotal(data.total || 0);
      setPage(p);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  }, [query, platform, format, country, sort]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    doSearch(1);
  };

  // Deep links: /search?q=<term> (e.g. from Website Intel's "spy similar ads").
  // window.location instead of useSearchParams — the latter needs a Suspense
  // boundary for next build's static prerender. A ref (not just setQuery)
  // hands the term to the initial search below, since state lands too late.
  const deepLinkQ = useRef<string | null>(null);
  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) {
      deepLinkQ.current = q;
      setQuery(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-load the best-performing ads on open, and re-run when a filter/sort
  // changes. Keyword typing still waits for an explicit submit.
  useEffect(() => {
    doSearch(1, deepLinkQ.current ?? undefined);
    deepLinkQ.current = null; // only the very first search uses the deep link
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [platform, format, country, sort]);

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto">
      <PageHeader
        icon={Search}
        gradient="from-[#3e86c6] to-[#a666aa]"
        title="Search ads"
        subtitle="Winning creatives across 13 markets — MENA core + global trends — ranked by what's printing money right now."
        live
      />

      {/* Search bar */}
      <form onSubmit={handleSubmit} className="relative mb-6 fade-up" style={{ ["--delay" as string]: "80ms" }}>
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by keyword, brand, or domain..."
          className="w-full pl-12 pr-28 py-3.5 bg-white border border-[#e6e6e7] rounded-full text-sm focus:outline-none focus:border-[#1d1d1f] transition"
        />
        <button
          type="submit"
          disabled={loading}
          className="btn-holo absolute right-2 top-1/2 -translate-y-1/2 px-5 py-2 text-sm disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          Search
        </button>
      </form>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-8 fade-up" style={{ ["--delay" as string]: "160ms" }}>
        <select
          value={platform}
          onChange={(e) => setPlatform(e.target.value as Platform)}
          className="px-4 py-2.5 border border-[#e6e6e7] rounded-full text-sm bg-white cursor-pointer hover:border-[#1d1d1f] transition"
        >
          <option value="all">All platforms</option>
          <option value="meta">Meta (FB + IG)</option>
          <option value="tiktok">TikTok</option>
        </select>

        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as AdFormat)}
          className="px-4 py-2.5 border border-[#e6e6e7] rounded-full text-sm bg-white cursor-pointer hover:border-[#1d1d1f] transition"
        >
          <option value="all">All formats</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="carousel">Carousel</option>
        </select>

        <select
          value={country}
          onChange={(e) => setCountry(e.target.value)}
          className="px-4 py-2.5 border border-[#e6e6e7] rounded-full text-sm bg-white cursor-pointer hover:border-[#1d1d1f] transition"
        >
          <option value="all">All countries</option>
          <optgroup label="Your markets">
            <option value="TN">Tunisia</option>
            <option value="DZ">Algeria</option>
            <option value="MA">Morocco</option>
            <option value="EG">Egypt</option>
            <option value="SA">Saudi Arabia</option>
            <option value="AE">UAE</option>
            <option value="KW">Kuwait</option>
            <option value="QA">Qatar</option>
          </optgroup>
          <optgroup label="🌍 Global trends">
            <option value="US">USA</option>
            <option value="CA">Canada</option>
            <option value="GB">UK</option>
            <option value="AU">Australia</option>
            <option value="FR">France</option>
          </optgroup>
        </select>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as SortBy)}
          className="px-4 py-2.5 border border-[#e6e6e7] rounded-full text-sm bg-white cursor-pointer hover:border-[#1d1d1f] transition"
        >
          <option value="best_performing">🔥 Printing money now</option>
          <option value="newest">Newest first</option>
          <option value="longest_running">Longest running</option>
          <option value="relevance">Most relevant</option>
        </select>
      </div>

      {/* Results — skeleton grid while loading so the layout never jumps */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No ads found</p>
          <p className="text-sm mt-2">Try different keywords or broaden your filters</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            {query ? (
              <p className="text-sm text-gray-500">
                {total.toLocaleString()} ads found
              </p>
            ) : (
              <p className="text-sm text-gray-500 flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-emerald-500" />
                {total.toLocaleString()} e-commerce winners — ranked by what&apos;s printing money right now (scaling velocity first)
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {results.map((ad, i) => (
              <Stagger key={ad.id || ad.ad_id} index={i}>
                <AdCard ad={ad} />
              </Stagger>
            ))}
          </div>

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              <button
                onClick={() => doSearch(page - 1)}
                disabled={page <= 1}
                className="px-4 py-2 text-sm border border-[#e6e6e7] rounded-full disabled:opacity-30 hover:border-[#1d1d1f] transition"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500 px-4">
                Page {page} of {Math.ceil(total / 20)}
              </span>
              <button
                onClick={() => doSearch(page + 1)}
                disabled={page >= Math.ceil(total / 20)}
                className="px-4 py-2 text-sm border border-[#e6e6e7] rounded-full disabled:opacity-30 hover:border-[#1d1d1f] transition"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

    </div>
  );
}
