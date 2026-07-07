"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Sparkles, Loader2, Radio, Layers, Lock, ArrowUpRight, Flame, TrendingUp, Gem } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { PageHeader, Stagger } from "@/components/PageHeader";
import { authFetch } from "@/lib/api";

interface Discovered {
  advertiser_name: string;
  advertiser_id: string | null;
  source: string;
  discovered_at: string;
  live_ads: number;
  total_variants: number;
  countries: string[];
  thumbnail: string | null;
}

// Friendly badge per discovery source — WHY this brand is on the shelf.
const SOURCE: Record<string, { label: string; icon: typeof Flame; cls: string }> = {
  hunter_tiktok_viral: { label: "Viral on TikTok", icon: Flame, cls: "from-[#ec4492] to-[#ee4454]" },
  hunter_rising_scaler: { label: "Scaling up fast", icon: TrendingUp, cls: "from-emerald-500 to-teal-500" },
  brand_deepdive: { label: "Top scaler", icon: Gem, cls: "from-violet-600 to-indigo-500" },
};

function timeAgo(iso: string): string {
  if (!iso) return "";
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function DiscoveredPage() {
  const { getToken, isLoaded } = useAuth();
  const [brands, setBrands] = useState<Discovered[]>([]);
  const [loading, setLoading] = useState(true);
  const [freeCapped, setFreeCapped] = useState(false);

  const load = useCallback(async () => {
    if (!isLoaded) return;
    setLoading(true);
    try {
      const res = await authFetch(getToken, "/api/brands/discovered");
      const data = res.ok ? await res.json() : { results: [] };
      setBrands(data.results || []);
      setFreeCapped(Boolean(data.free_capped));
    } catch {
      setBrands([]);
    } finally {
      setLoading(false);
    }
  }, [isLoaded, getToken]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto">
      <PageHeader
        icon={Sparkles}
        gradient="from-[#f05427] to-[#ec4492]"
        title="Just Discovered"
        subtitle="Winning brands we found this cycle — viral on TikTok or scaling hard on Meta — with their full catalogs pulled. Fresh winners, before your competitors notice."
        live
      />

      {loading && (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {!loading && brands.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-40" />
          <p className="text-lg font-semibold text-gray-500">The hunt is warming up…</p>
          <p className="text-sm mt-1">Freshly discovered winning brands land here after each discovery pass.</p>
        </div>
      )}

      {!loading && brands.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {brands.map((b, i) => {
            const src = SOURCE[b.source] ?? SOURCE.brand_deepdive;
            return (
              <Stagger key={b.advertiser_id || b.advertiser_name} index={i}>
                <Link
                  href={b.advertiser_id ? `/brands/${b.advertiser_id}` : "#"}
                  className="group block bg-white border border-[#e6e6e7] rounded-2xl overflow-hidden hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 h-full"
                >
                  <div className="aspect-video bg-gray-100 relative overflow-hidden">
                    {b.thumbnail ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={b.thumbnail}
                        alt={b.advertiser_name}
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.04]"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-3xl font-black text-gray-300">
                        {b.advertiser_name.charAt(0).toUpperCase()}
                      </div>
                    )}
                    <span className={`absolute top-3 left-3 flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold text-white shadow-sm bg-gradient-to-r ${src.cls}`}>
                      <src.icon className="w-3 h-3" /> {src.label}
                    </span>
                    <span className="absolute bottom-3 right-3 text-[11px] font-medium text-white/90 bg-black/40 px-2 py-0.5 rounded-full backdrop-blur-sm">
                      {timeAgo(b.discovered_at)}
                    </span>
                  </div>
                  <div className="p-4">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="font-bold text-gray-900 truncate">{b.advertiser_name}</span>
                      <ArrowUpRight className="w-4 h-4 text-gray-300 group-hover:text-[#1d1d1f] transition shrink-0" />
                    </div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                      {b.live_ads > 0 && (
                        <span className="flex items-center gap-1 font-semibold text-rose-600" title="Verified ads live in the Ad Library right now">
                          <Radio className="w-3.5 h-3.5" /> {b.live_ads} live now
                        </span>
                      )}
                      {b.total_variants > 0 && (
                        <span className="flex items-center gap-1 text-emerald-600" title="Total creative scaling">
                          <Layers className="w-3.5 h-3.5" /> {b.total_variants}× scaling
                        </span>
                      )}
                      {b.countries.length > 0 && <span>{b.countries.slice(0, 4).join(" · ")}</span>}
                    </div>
                  </div>
                </Link>
              </Stagger>
            );
          })}
        </div>
      )}

      {!loading && freeCapped && (
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl p-5 text-white holo-gradient">
          <div className="flex items-center gap-3">
            <Lock className="w-5 h-5 shrink-0" />
            <p className="text-sm font-semibold">
              Pro members see every freshly discovered winner the moment we find it — you&apos;re seeing a preview.
            </p>
          </div>
          <Link
            href="/pricing"
            className="shrink-0 px-5 py-2.5 bg-white text-[#1d1d1f] rounded-full text-sm font-bold hover:scale-[1.03] transition"
          >
            Unlock the full feed
          </Link>
        </div>
      )}
    </div>
  );
}
