"use client";

import { useEffect, useState, useCallback } from "react";
import { Bookmark, Loader2 } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { AdCard } from "@/components/ads/AdCard";
import { useSaved } from "@/components/SavedProvider";
import { authFetch } from "@/lib/api";
import { Ad } from "@/types";

export default function SavedPage() {
  const { savedIds } = useSaved();
  const { getToken, isLoaded } = useAuth();
  const [ads, setAds] = useState<Ad[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!isLoaded) return;
    setLoading(true);
    try {
      const res = await authFetch(getToken, "/api/user/saved/ads");
      const data = res.ok ? await res.json() : { results: [] };
      setAds(data.results || []);
    } catch {
      setAds([]);
    } finally {
      setLoading(false);
    }
  }, [isLoaded, getToken]);

  useEffect(() => {
    load();
  }, [load]);

  // Reflect un-saves live: only show ads still in the saved set.
  const visible = ads.filter((a) => savedIds.has(a.id || a.ad_id));

  return (
    <div className="p-8 max-w-7xl">
      <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
        <Bookmark className="w-6 h-6" /> Saved ads
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        Your swipe file of winning ads. {visible.length > 0 && `${visible.length} saved.`}
      </p>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {!loading && visible.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <Bookmark className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">No saved ads yet</p>
          <p className="text-sm mt-2">
            Hit the bookmark on any ad in Search to build your swipe file.
          </p>
        </div>
      )}

      {!loading && visible.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {visible.map((ad) => (
            <AdCard key={ad.id || ad.ad_id} ad={ad} />
          ))}
        </div>
      )}
    </div>
  );
}
