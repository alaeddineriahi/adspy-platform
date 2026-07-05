"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import {
  Radar, Flame, Zap, Globe2, TrendingUp, Layers, Lock, Eye,
  Loader2, ArrowUpRight, Clock,
} from "lucide-react";
import { authFetch, errMessage } from "@/lib/api";

interface RadarEvent {
  id: string;
  event_type: string;
  country: string | null;
  ad_id: string | null;
  advertiser_id: string | null;
  advertiser_name: string | null;
  headline: string;
  detail: string | null;
  magnitude: number | null;
  heat: number | null;
  thumbnail: string | null;
  created_at: string | null;
  watched: boolean;
  locked: boolean;
}
interface RadarResponse {
  plan: string;
  window_days: number;
  counts: Record<string, number>;
  locked_count: number;
  events: RadarEvent[];
}

const TYPES: Record<string, { label: string; icon: typeof Flame; grad: string; text: string }> = {
  new_hot: { label: "Scaling fast", icon: Flame, grad: "from-orange-500 to-red-500", text: "text-orange-600" },
  momentum_flip: { label: "Caught fire", icon: Zap, grad: "from-pink-500 to-rose-500", text: "text-pink-600" },
  trend_arrival: { label: "Wave arriving", icon: Globe2, grad: "from-blue-500 to-indigo-500", text: "text-blue-600" },
  brand_escalation: { label: "Budget pouring in", icon: TrendingUp, grad: "from-emerald-500 to-teal-500", text: "text-emerald-600" },
  brand_expansion: { label: "New creatives", icon: Layers, grad: "from-violet-500 to-purple-500", text: "text-violet-600" },
};

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 3600) return `${Math.max(1, Math.floor(s / 60))}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/** The animated dish: concentric rings, a sweeping beam, one blip per signal. */
function RadarDish({ blips }: { blips: number }) {
  // Deterministic pseudo-random blip positions so they don't jump on re-render.
  const points = useMemo(() => {
    const n = Math.min(blips, 8);
    return Array.from({ length: n }, (_, i) => {
      const angle = (i * 137.5 * Math.PI) / 180; // golden-angle spread
      const r = 18 + ((i * 29) % 30);            // 18–48% of radius
      return {
        left: 50 + r * Math.cos(angle),
        top: 50 + r * Math.sin(angle),
        delay: i * 350,
      };
    });
  }, [blips]);

  return (
    <div className="relative w-36 h-36 md:w-44 md:h-44 shrink-0" aria-hidden>
      <div className="absolute inset-0 rounded-full border border-[#e6e6e7] bg-white" />
      <div className="absolute inset-[18%] rounded-full border border-[#e6e6e7]/80" />
      <div className="absolute inset-[36%] rounded-full border border-[#e6e6e7]/60" />
      <div className="absolute left-1/2 top-1/2 w-1.5 h-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#1d1d1f]" />
      <div className="radar-beam absolute inset-0 rounded-full" />
      {points.map((p, i) => (
        <span
          key={i}
          className="radar-blip absolute w-1.5 h-1.5 rounded-full bg-[#ec4492]"
          style={{ left: `${p.left}%`, top: `${p.top}%`, ["--delay" as string]: `${p.delay}ms` }}
        />
      ))}
    </div>
  );
}

export default function RadarPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<RadarResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [country, setCountry] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const load = useCallback(async (c: string) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ limit: "80" });
      if (c) params.set("country", c);
      const res = await authFetch(getToken, `/api/radar?${params}`);
      if (!res.ok) throw new Error(`Radar unavailable (${res.status})`);
      setData(await res.json());
    } catch (e) {
      setError(errMessage(e, "Couldn't load the radar."));
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load("");
  }, [load]);

  const events = useMemo(
    () => (data?.events || []).filter((e) => !typeFilter || e.event_type === typeFilter),
    [data, typeFilter],
  );
  const countries = useMemo(
    () => Array.from(new Set((data?.events || []).map((e) => e.country).filter(Boolean))) as string[],
    [data],
  );
  const typeCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const e of data?.events || []) m[e.event_type] = (m[e.event_type] || 0) + 1;
    return m;
  }, [data]);

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      {/* Header with the dish */}
      <div className="flex items-center justify-between gap-6 mb-8">
        <div className="fade-up" style={{ ["--delay" as string]: "0ms" }}>
          <h2 className="text-2xl font-black tracking-tight text-[#1d1d1f] flex items-center gap-2.5">
            <Radar className="w-6 h-6" /> Trend Radar
            <span className="radar-live-dot w-2 h-2 rounded-full bg-[#ec4492]" />
          </h2>
          <p className="text-sm text-gray-500 mt-1 max-w-md">
            What started printing money since you last looked — watching 13 markets
            around the clock, so you catch the wave days before everyone else.
          </p>
          {data && (
            <p className="text-xs text-gray-400 mt-2 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              Last {data.window_days} days · {data.counts.total} signals
              {data.locked_count > 0 && ` · ${data.locked_count} locked`}
            </p>
          )}
        </div>
        <div className="fade-up hidden sm:block" style={{ ["--delay" as string]: "120ms" }}>
          <RadarDish blips={Math.max(events.length, 3)} />
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 mb-6 fade-up" style={{ ["--delay" as string]: "180ms" }}>
        <button
          onClick={() => setTypeFilter("")}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
            !typeFilter ? "bg-[#1d1d1f] text-white border-[#1d1d1f]" : "bg-white text-gray-600 border-[#e6e6e7] hover:border-[#1d1d1f]"
          }`}
        >
          All signals
        </button>
        {Object.entries(TYPES).map(([key, t]) =>
          typeCounts[key] ? (
            <button
              key={key}
              onClick={() => setTypeFilter(typeFilter === key ? "" : key)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                typeFilter === key ? "bg-[#1d1d1f] text-white border-[#1d1d1f]" : "bg-white text-gray-600 border-[#e6e6e7] hover:border-[#1d1d1f]"
              }`}
            >
              <t.icon className="w-3.5 h-3.5" /> {t.label} · {typeCounts[key]}
            </button>
          ) : null,
        )}
        <select
          value={country}
          onChange={(e) => { setCountry(e.target.value); load(e.target.value); }}
          className="ml-auto px-3 py-1.5 border border-[#e6e6e7] rounded-full text-xs bg-white"
        >
          <option value="">🌐 All markets</option>
          {countries.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {loading && (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}
      {error && <p className="text-sm text-red-600 py-8 text-center">{error}</p>}

      {!loading && !error && events.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <Radar className="w-12 h-12 mx-auto mb-4 opacity-40" />
          <p className="text-lg font-semibold text-gray-500">The radar is sweeping…</p>
          <p className="text-sm mt-1">Signals appear here as soon as a product starts scaling in any of your 13 markets.</p>
        </div>
      )}

      {/* Upsell banner for locked signals */}
      {!loading && (data?.locked_count ?? 0) > 0 && (
        <div className="flex items-center justify-between gap-4 rounded-2xl p-4 mb-5 text-white holo-gradient fade-up" style={{ ["--delay" as string]: "220ms" }}>
          <p className="text-sm font-semibold flex items-center gap-2">
            <Lock className="w-4 h-4" />
            {data!.locked_count} more signals fired this week — Pro members saw them first.
          </p>
          <Link href="/pricing" className="shrink-0 px-4 py-2 bg-white text-[#1d1d1f] rounded-full text-sm font-bold hover:scale-[1.03] transition">
            Unlock radar
          </Link>
        </div>
      )}

      {/* Event feed */}
      <div className="space-y-3">
        {events.map((e, i) => {
          const t = TYPES[e.event_type] ?? TYPES.new_hot;
          const href = e.ad_id ? `/creative/${e.ad_id}` : e.advertiser_id ? `/brands/${e.advertiser_id}` : null;
          return (
            <div
              key={e.id}
              className={`fade-up bg-white border border-[#e6e6e7] rounded-2xl p-4 flex items-center gap-4 transition hover:shadow-md hover:-translate-y-0.5 ${
                e.locked ? "radar-locked" : ""
              }`}
              style={{ ["--delay" as string]: `${Math.min(i, 10) * 60 + 250}ms` }}
            >
              <span className={`w-11 h-11 shrink-0 rounded-xl flex items-center justify-center text-white bg-gradient-to-br ${t.grad}`}>
                <t.icon className="w-5 h-5" />
              </span>

              <div className={`min-w-0 flex-1 ${e.locked ? "blur-[5px] select-none" : ""}`}>
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-bold text-[#1d1d1f] truncate">{e.headline}</p>
                  {e.watched && (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-white bg-[#1d1d1f] px-1.5 py-0.5 rounded">
                      <Eye className="w-3 h-3" /> WATCHED
                    </span>
                  )}
                </div>
                {e.detail && <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{e.detail}</p>}
                <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-400">
                  <span className={`font-semibold ${t.text}`}>{t.label}</span>
                  {e.country && <span>{e.country}</span>}
                  {typeof e.magnitude === "number" && e.magnitude > 0 && (
                    <span className="font-semibold text-gray-600">+{e.magnitude}</span>
                  )}
                  <span>{timeAgo(e.created_at)}</span>
                </div>
              </div>

              {e.thumbnail && !e.locked && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={e.thumbnail} alt="" className="w-16 h-16 rounded-xl object-cover shrink-0 hidden sm:block" />
              )}

              {e.locked ? (
                <Link
                  href="/pricing"
                  className="shrink-0 flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-bold text-white holo-gradient relative z-10"
                >
                  <Lock className="w-3.5 h-3.5" /> Unlock
                </Link>
              ) : href ? (
                <Link
                  href={href}
                  className="shrink-0 flex items-center gap-1 px-3.5 py-2 rounded-full text-xs font-semibold border border-[#e6e6e7] hover:border-[#1d1d1f] transition"
                >
                  View <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
