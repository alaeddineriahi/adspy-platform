"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Eye, Loader2, Layers, Clock, TrendingUp, Radio, ArrowUpRight } from "lucide-react";
import { AdCard } from "@/components/ads/AdCard";
import { API_URL } from "@/lib/api";
import { Ad } from "@/types";

interface TrajectoryPoint {
  live_ads: number;
  at: string | null;
}

export default function BrandDetailPage() {
  const { id } = useParams();
  const [ads, setAds] = useState<Ad[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([]);
  const [growth, setGrowth] = useState<number | null>(null);

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
    fetch(`${API_URL}/api/brands/${id}/trajectory`)
      .then((r) => (r.ok ? r.json() : { points: [], growth: null }))
      .then((d) => {
        setTrajectory(d.points || []);
        setGrowth(d.growth ?? null);
      })
      .catch(() => setTrajectory([]));
  }, [id]);

  const name = ads[0]?.advertiser_name || "Brand";
  const liveNow = trajectory.length
    ? trajectory[trajectory.length - 1].live_ads
    : ads.find((a) => (a.brand_live_ads ?? 0) > 0)?.brand_live_ads ?? 0;
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
    <div className="p-4 md:p-8 max-w-7xl mx-auto">
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
            <h2 className="text-2xl font-black tracking-tight text-[#1d1d1f] flex items-center gap-2">
              <Eye className="w-6 h-6" /> {name}
            </h2>
            <span className="flex items-center gap-2 shrink-0">
              {liveNow > 0 && (
                <span
                  className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg font-bold text-white bg-gradient-to-r from-rose-500 to-orange-500"
                  title="Verified: total ads this brand has live in the Ad Library right now"
                >
                  <Radio className="w-3.5 h-3.5" /> {liveNow} ads live now
                </span>
              )}
              <span className="text-xs px-2.5 py-1.5 bg-green-100 text-green-700 rounded-lg">
                {activeCount} active
              </span>
            </span>
          </div>

          {growth !== null && growth > 0 && (
            <p className="flex items-center gap-1.5 text-sm font-semibold text-emerald-600 mb-2">
              <ArrowUpRight className="w-4 h-4" />
              Scaling up: +{growth} live ads since we started tracking
              ({trajectory[0]?.live_ads} → {liveNow})
            </p>
          )}

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
