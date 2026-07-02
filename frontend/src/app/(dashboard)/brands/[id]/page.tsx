"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Eye, Loader2, Layers, Clock, TrendingUp } from "lucide-react";
import { AdCard } from "@/components/ads/AdCard";
import { API_URL } from "@/lib/api";
import { Ad } from "@/types";

export default function BrandDetailPage() {
  const { id } = useParams();
  const [ads, setAds] = useState<Ad[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    fetch(`${API_URL}/api/brands/${id}/creatives?limit=60`)
      .then((r) => (r.ok ? r.json() : { results: [], total: 0 }))
      .then((d) => {
        setAds(d.results || []);
        setTotal(d.total || 0);
      })
      .catch(() => setAds([]))
      .finally(() => setLoading(false));
  }, [id]);

  const name = ads[0]?.advertiser_name || "Brand";
  const countries = Array.from(new Set(ads.map((a) => a.country).filter(Boolean)));
  const maxDays = Math.max(0, ...ads.map((a) => a.days_running || 0));
  const totalVariants = ads.reduce((s, a) => s + (a.variant_count || 0), 0);
  const activeCount = ads.filter((a) => a.is_active).length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl">
      <Link
        href="/brands"
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-4"
      >
        <ArrowLeft className="w-4 h-4" /> Brand Spy
      </Link>

      {ads.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <Eye className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No ads found for this brand</p>
          <p className="text-sm mt-2">
            It may have been cleaned out of the index — head back and pick another one.
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-4 mb-2">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Eye className="w-6 h-6" /> {name}
            </h2>
            <span className="text-xs px-2.5 py-1.5 bg-green-100 text-green-700 rounded-lg shrink-0">
              {activeCount} active
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-gray-500 mb-6">
            <span className="flex items-center gap-1.5" title="Total creative variants (scaling = budget)">
              <Layers className="w-4 h-4 text-emerald-500" /> {totalVariants}× scaling
            </span>
            <span className="flex items-center gap-1.5" title="Longest a creative has stayed live">
              <Clock className="w-4 h-4" /> up to {maxDays}d running
            </span>
            <span className="flex items-center gap-1.5">
              <TrendingUp className="w-4 h-4" /> {total} winning ads
            </span>
            {countries.length > 0 && <span>{countries.join(" · ")}</span>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {ads.map((ad) => (
              <AdCard key={ad.id || ad.ad_id} ad={ad} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
