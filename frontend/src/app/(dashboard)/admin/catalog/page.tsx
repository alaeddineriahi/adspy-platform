"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { Loader2, Search, Trash2, Database } from "lucide-react";
import { adminApi } from "@/lib/admin";
import { errMessage } from "@/lib/api";

interface CatalogOverview {
  total_ads: number;
  active_ads: number;
  by_country: Record<string, number>;
  by_format: Record<string, number>;
  top_brands: { advertiser_name: string; total_variants: number }[];
}
interface AdRow {
  id: string; advertiser_name: string; country: string; ad_format: string;
  is_active: boolean; days_running: number; copy_text: string;
}

export default function AdminCatalogPage() {
  const { getToken } = useAuth();
  const [overview, setOverview] = useState<CatalogOverview | null>(null);
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("");
  const [ads, setAds] = useState<AdRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState("");
  const [error, setError] = useState("");

  const loadAds = useCallback(async () => {
    try {
      const d = await adminApi.browseAds(getToken, q, country);
      setAds(d.results);
      setTotal(d.total);
    } catch (e) {
      setError(errMessage(e));
    }
  }, [getToken, q, country]);

  useEffect(() => {
    setLoading(true);
    Promise.all([adminApi.catalogOverview(getToken).then(setOverview), loadAds()])
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [getToken]);

  const remove = async (id: string) => {
    if (!confirm("Delete this ad from the catalog? This can't be undone.")) return;
    setDeleting(id);
    try {
      await adminApi.deleteAd(getToken, id);
      setAds((prev) => prev.filter((a) => a.id !== id));
      setTotal((t) => t - 1);
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setDeleting("");
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {error && <p className="text-sm text-red-600">{error}</p>}

      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center gap-2 text-xs font-medium text-gray-500 mb-2">
              <Database className="w-4 h-4" /> Catalog size
            </div>
            <p className="text-2xl font-bold text-gray-900">{overview.total_ads}</p>
            <p className="text-xs text-gray-400 mt-1">{overview.active_ads} active</p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs font-medium text-gray-500 mb-2">By format</p>
            {Object.entries(overview.by_format).map(([f, c]) => (
              <p key={f} className="text-sm text-gray-700 flex justify-between">
                <span className="capitalize">{f}</span> <span className="text-gray-400">{c}</span>
              </p>
            ))}
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="text-xs font-medium text-gray-500 mb-2">Top brands (scaling)</p>
            {overview.top_brands.slice(0, 4).map((b) => (
              <p key={b.advertiser_name} className="text-sm text-gray-700 truncate flex justify-between gap-2">
                <span className="truncate">{b.advertiser_name}</span>
                <span className="text-gray-400 shrink-0">{b.total_variants}×</span>
              </p>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">
          Moderation — browse & remove ({total})
        </h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            loadAds();
          }}
          className="flex gap-2 mb-4 max-w-lg"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search copy text…"
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="border border-gray-300 rounded-lg text-sm px-3"
          >
            <option value="">All countries</option>
            {["TN", "MA", "DZ", "EG", "SA", "AE"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button type="submit" className="px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-800">
            Filter
          </button>
        </form>

        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100 bg-gray-50">
                <th className="py-2.5 px-4">Advertiser</th>
                <th className="py-2.5 px-4">Copy</th>
                <th className="py-2.5 px-4">Country</th>
                <th className="py-2.5 px-4">Format</th>
                <th className="py-2.5 px-4">Days</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4"></th>
              </tr>
            </thead>
            <tbody>
              {ads.map((ad) => (
                <tr key={ad.id} className="border-b border-gray-50">
                  <td className="py-2 px-4 font-medium text-gray-800 whitespace-nowrap">{ad.advertiser_name}</td>
                  <td className="py-2 px-4 text-gray-500 max-w-xs truncate">{ad.copy_text}</td>
                  <td className="py-2 px-4 text-gray-600">{ad.country}</td>
                  <td className="py-2 px-4 text-gray-600">{ad.ad_format}</td>
                  <td className="py-2 px-4 text-gray-600">{ad.days_running}</td>
                  <td className="py-2 px-4">
                    <span className={ad.is_active ? "text-emerald-600" : "text-gray-400"}>
                      {ad.is_active ? "active" : "stale"}
                    </span>
                  </td>
                  <td className="py-2 px-4">
                    <button
                      onClick={() => remove(ad.id)}
                      disabled={deleting === ad.id}
                      className="text-red-500 hover:text-red-700 disabled:opacity-40"
                      title="Delete this ad"
                    >
                      {deleting === ad.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    </button>
                  </td>
                </tr>
              ))}
              {ads.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400">No ads match.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
