"use client";

import { useEffect, useState, useCallback } from "react";
import { Bookmark, Folder } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { AdCard } from "@/components/ads/AdCard";
import { PageHeader, Stagger } from "@/components/PageHeader";
import { SkeletonCard } from "@/components/ads/SkeletonCard";
import { useSaved } from "@/components/SavedProvider";
import { authFetch } from "@/lib/api";
import { Ad } from "@/types";

interface Board {
  name: string;
  count: number;
}

export default function SavedPage() {
  const { savedIds } = useSaved();
  const { getToken, isLoaded } = useAuth();
  const [ads, setAds] = useState<Ad[]>([]);
  const [boards, setBoards] = useState<Board[]>([]);
  const [board, setBoard] = useState<string>(""); // "" = all boards
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    async (selected: string) => {
      if (!isLoaded) return;
      setLoading(true);
      try {
        const qs = selected ? `?board=${encodeURIComponent(selected)}` : "";
        const [adsRes, boardsRes] = await Promise.all([
          authFetch(getToken, `/api/user/saved/ads${qs}`),
          authFetch(getToken, "/api/user/saved"),
        ]);
        const adsData = adsRes.ok ? await adsRes.json() : { results: [] };
        setAds(adsData.results || []);
        if (boardsRes.ok) {
          const b = await boardsRes.json();
          setBoards(b.boards || []);
        }
      } catch {
        setAds([]);
      } finally {
        setLoading(false);
      }
    },
    [isLoaded, getToken]
  );

  useEffect(() => {
    load(board);
  }, [load, board]);

  // Reflect un-saves live: only show ads still in the saved set.
  const visible = ads.filter((a) => savedIds.has(a.id || a.ad_id));
  // Board tabs only earn their space once the user has organized anything
  // beyond the default board.
  const showTabs = boards.length > 1 || (boards.length === 1 && boards[0].name !== "Default");

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto">
      <PageHeader
        icon={Bookmark}
        gradient="from-[#f05427] to-[#3e86c6]"
        title="Saved ads"
        subtitle={`Your swipe file of winning ads.${visible.length > 0 ? ` ${visible.length} saved.` : ""}`}
      />

      {showTabs && (
        <div className="flex flex-wrap items-center gap-2 mb-6">
          <button
            onClick={() => setBoard("")}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition ${
              !board
                ? "bg-[#1d1d1f] text-white border-[#1d1d1f]"
                : "bg-white text-gray-600 border-[#e6e6e7] hover:border-[#1d1d1f]"
            }`}
          >
            All boards
          </button>
          {boards.map((b) => (
            <button
              key={b.name}
              onClick={() => setBoard(board === b.name ? "" : b.name)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition ${
                board === b.name
                  ? "bg-[#1d1d1f] text-white border-[#1d1d1f]"
                  : "bg-white text-gray-600 border-[#e6e6e7] hover:border-[#1d1d1f]"
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              {b.name} · {b.count}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!loading && visible.length === 0 && (
        <div className="text-center py-20 text-gray-400">
          <Bookmark className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p className="text-lg">{board ? `Nothing on “${board}” yet` : "No saved ads yet"}</p>
          <p className="text-sm mt-2">
            Hit the bookmark on any ad in Search to build your swipe file.
          </p>
        </div>
      )}

      {!loading && visible.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {visible.map((ad, i) => (
            <Stagger key={ad.id || ad.ad_id} index={i}>
              <AdCard ad={ad} />
            </Stagger>
          ))}
        </div>
      )}
    </div>
  );
}
