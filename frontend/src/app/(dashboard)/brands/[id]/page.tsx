"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Eye, Loader2, Layers, Clock, TrendingUp, Radio, ArrowUpRight, BellRing, Bell } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { AdCard } from "@/components/ads/AdCard";
import { Stagger } from "@/components/PageHeader";
import { authFetch } from "@/lib/api";
import { Ad } from "@/types";

interface TrajectoryPoint {
  live_ads: number;
  at: string | null;
}

interface TimelineCreative {
  id: string;
  copy_excerpt: string;
  thumbnail?: string;
  days_running?: number;
  is_active: boolean;
  variant_count?: number;
  momentum?: string;
}

interface TimelineMonth {
  month: string; // "2026-05"
  launched: number;
  still_active: number;
  creatives: TimelineCreative[];
}

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function monthLabel(m: string): string {
  const [y, mo] = m.split("-").map(Number);
  return Number.isFinite(mo) ? `${MONTH_NAMES[mo - 1]} ${String(y).slice(2)}` : m;
}

export default function BrandDetailPage() {
  const { id } = useParams();
  const { getToken } = useAuth();
  const [ads, setAds] = useState<Ad[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([]);
  const [growth, setGrowth] = useState<number | null>(null);
  const [timeline, setTimeline] = useState<TimelineMonth[]>([]);
  const [watched, setWatched] = useState(false);
  const [togglingWatch, setTogglingWatch] = useState(false);

  useEffect(() => {
    if (!id) return;
    authFetch(getToken, `/api/brands/${id}/creatives?limit=60`)
      .then((r) => (r.ok ? r.json() : { results: [], total: 0 }))
      .then((d) => {
        setAds(d.results || []);
        setTotal(d.total || 0);
      })
      .catch(() => setAds([]))
      .finally(() => setLoading(false));
    authFetch(getToken, `/api/brands/${id}/trajectory`)
      .then((r) => (r.ok ? r.json() : { points: [], growth: null }))
      .then((d) => {
        setTrajectory(d.points || []);
        setGrowth(d.growth ?? null);
      })
      .catch(() => setTrajectory([]));
    authFetch(getToken, `/api/brands/${id}/timeline`)
      .then((r) => (r.ok ? r.json() : { months: [] }))
      .then((d) => setTimeline(d.months || []))
      .catch(() => setTimeline([]));
    authFetch(getToken, "/api/brands/watchlist")
      .then((r) => (r.ok ? r.json() : { brands: [] }))
      .then((d: { brands: { brand_id: string }[] }) =>
        setWatched((d.brands || []).some((b) => b.brand_id === id)),
      )
      .catch(() => {});
  }, [id, getToken]);

  const toggleWatch = async () => {
    setTogglingWatch(true);
    const next = !watched;
    setWatched(next); // optimistic — revert on failure
    try {
      const res = await authFetch(
        getToken,
        next ? "/api/brands/watchlist" : "/api/brands/watchlist/remove",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ brand_id: id, brand_name: ads[0]?.advertiser_name }),
        },
      );
      if (!res.ok) setWatched(!next);
    } catch {
      setWatched(!next);
    } finally {
      setTogglingWatch(false);
    }
  };

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
          <div className="flex items-start justify-between gap-4 mb-2 fade-up" style={{ ["--delay" as string]: "0ms" }}>
            <h2 className="text-2xl font-black tracking-tight text-[#1d1d1f] flex items-center gap-2">
              <Eye className="w-6 h-6" /> {name}
            </h2>
            <span className="flex items-center gap-2 shrink-0">
              <button
                onClick={toggleWatch}
                disabled={togglingWatch}
                title={watched ? "Stop watching — no more radar alerts for this brand" : "Watch this brand — its moves show up on your Trend Radar"}
                className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-semibold border transition ${
                  watched
                    ? "bg-[#1d1d1f] text-white border-[#1d1d1f]"
                    : "bg-white text-gray-700 border-[#e6e6e7] hover:border-[#1d1d1f]"
                }`}
              >
                {watched ? <BellRing className="w-3.5 h-3.5" /> : <Bell className="w-3.5 h-3.5" />}
                {watched ? "Watching" : "Watch"}
              </button>
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

          {/* Creative launch timeline — the brand's testing cadence at a glance */}
          {timeline.length >= 2 && (
            <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 mb-6 fade-up" style={{ ["--delay" as string]: "120ms" }}>
              <h3 className="text-sm font-bold text-[#1d1d1f] mb-1 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-violet-500" /> Creative launch history
              </h3>
              <p className="text-xs text-gray-500 mb-4">
                When each creative went live and which survived — bursts of short-lived launches followed by a long
                runner are this brand&apos;s winning-test pattern.
              </p>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {timeline.map((m) => (
                  <div key={m.month} className="shrink-0 w-36 border border-[#f0f0f1] rounded-xl p-3">
                    <p className="text-[11px] font-bold text-gray-500 uppercase">{monthLabel(m.month)}</p>
                    <p className="text-lg font-black text-[#1d1d1f] leading-tight">
                      {m.launched}
                      <span className="text-[11px] font-semibold text-gray-400"> launched</span>
                    </p>
                    <p className={`text-[11px] font-semibold mb-2 ${m.still_active ? "text-emerald-600" : "text-gray-400"}`}>
                      {m.still_active ? `${m.still_active} still alive` : "all killed"}
                    </p>
                    <div className="flex -space-x-2">
                      {m.creatives.slice(0, 4).map((c) =>
                        c.thumbnail ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            key={c.id}
                            src={c.thumbnail}
                            alt=""
                            title={`${c.copy_excerpt}${c.is_active ? " · still live" : " · killed"}`}
                            onClick={() => (window.location.href = `/creative/${c.id}`)}
                            className={`w-8 h-8 rounded-lg object-cover border-2 cursor-pointer hover:scale-110 transition ${
                              c.is_active ? "border-emerald-400" : "border-gray-200 grayscale"
                            }`}
                          />
                        ) : (
                          <span
                            key={c.id}
                            title={c.copy_excerpt}
                            onClick={() => (window.location.href = `/creative/${c.id}`)}
                            className={`w-8 h-8 rounded-lg border-2 bg-gray-100 cursor-pointer ${
                              c.is_active ? "border-emerald-400" : "border-gray-200"
                            }`}
                          />
                        ),
                      )}
                      {m.creatives.length > 4 && (
                        <span className="w-8 h-8 rounded-lg border-2 border-white bg-gray-900 text-white text-[10px] font-bold flex items-center justify-center">
                          +{m.creatives.length - 4}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {ads.map((ad, i) => (
              <Stagger key={ad.id || ad.ad_id} index={i}>
                <AdCard ad={ad} />
              </Stagger>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
