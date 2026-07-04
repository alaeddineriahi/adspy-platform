"use client";

import { useState, useCallback, useEffect } from "react";
import { Eye, Search, Loader2, TrendingUp, Layers, Clock, Radio } from "lucide-react";
import Link from "next/link";
import { Brand } from "@/types";
import { PageHeader, Stagger } from "@/components/PageHeader";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function BrandsPage() {
  const [query, setQuery] = useState("");
  const [bigOnly, setBigOnly] = useState(false); // "50+ ads live" quality cut
  const [brands, setBrands] = useState<Brand[]>([]);
  const [loading, setLoading] = useState(true);
  const [searched, setSearched] = useState(false);

  const load = useCallback(async (q: string, big: boolean) => {
    setLoading(true);
    setSearched(true);
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (big) params.set("min_live_ads", "50");
      params.set("limit", "24");
      const res = await fetch(`${API_URL}/api/brands/search?${params}`);
      const data = await res.json();
      setBrands(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Show the money-printing leaderboard on open; the box just filters it by name.
  useEffect(() => {
    load("", false);
  }, [load]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    load(query, bigOnly);
  };

  const toggleBig = () => {
    const next = !bigOnly;
    setBigOnly(next);
    load(query, next);
  };

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      <PageHeader
        icon={Eye}
        gradient="from-[#a666aa] to-[#ec4492]"
        title="Brand Spy"
        subtitle="The advertisers printing the most money — verified live-ad counts, scaling totals, and trajectory."
        live
      />

      <form onSubmit={submit} className="relative mb-8 fade-up" style={{ ["--delay" as string]: "80ms" }}>
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter advertisers by name..."
          className="w-full pl-12 pr-4 py-3.5 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </form>

      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={toggleBig}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
            bigOnly
              ? "bg-[#1d1d1f] text-white border-[#1d1d1f]"
              : "bg-white text-gray-600 border-[#e6e6e7] hover:border-[#1d1d1f]"
          }`}
          title="Only brands we've verified are running 50+ ads in the Ad Library right now"
        >
          <Radio className="w-3.5 h-3.5" /> 50+ ads live
        </button>
      </div>

      {!loading && (
        <p className="text-sm text-gray-500 mb-4 flex items-center gap-1.5">
          <TrendingUp className="w-4 h-4 text-emerald-500" />
          {bigOnly
            ? `${brands.length} verified heavy spenders — 50+ ads live in the Ad Library right now`
            : query
            ? `${brands.length} brands matching "${query}"`
            : "Brands printing the most money — ranked by total creative scaling"}
        </p>
      )}

      {loading && (
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {!loading && searched && brands.length === 0 && (
        <p className="text-center text-gray-400 py-16">No brands found.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {brands.map((b, i) => (
          <Stagger key={b.advertiser_id || b.advertiser_name} index={i}>
          <Link
            href={`/brands/${b.advertiser_id}`}
            className="block bg-white border border-[#e6e6e7] rounded-2xl p-5 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-gray-900 truncate">
                {!query && (
                  <span className="text-gray-400 mr-1.5">#{i + 1}</span>
                )}
                {b.advertiser_name}
              </span>
              <span className="flex items-center gap-1.5 shrink-0">
                {(b.live_ads ?? 0) > 0 && (
                  <span
                    className="text-xs px-2 py-1 rounded font-bold text-white bg-gradient-to-r from-rose-500 to-orange-500"
                    title="Verified: total ads this brand has live in the Ad Library right now"
                  >
                    {b.live_ads} live now
                  </span>
                )}
                <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                  {b.active_ads} active
                </span>
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-3 text-xs text-gray-500">
              <span className="flex items-center gap-1" title="Total creative variants (scaling = budget)">
                <Layers className="w-3.5 h-3.5 text-emerald-500" />
                {b.total_variants ?? b.total_ads}× scaling
              </span>
              <span className="flex items-center gap-1" title="Longest a creative has stayed live">
                <Clock className="w-3.5 h-3.5" />
                up to {b.max_days ?? 0}d
              </span>
              {typeof b.top_score === "number" && (
                <span className="flex items-center gap-1" title="Best ad's money score (0–100)">
                  <TrendingUp className="w-3.5 h-3.5" />
                  {b.top_score} score
                </span>
              )}
            </div>

            <p className="text-xs text-gray-400 mt-2">
              {b.total_ads} winning ads · {b.countries?.join(", ")}
            </p>
          </Link>
          </Stagger>
        ))}
      </div>
    </div>
  );
}
