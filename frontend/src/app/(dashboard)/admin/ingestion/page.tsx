"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { Download, Loader2, Play, CheckCircle2, XCircle, RefreshCw, AlertTriangle, Activity } from "lucide-react";
import { authFetch, apiError, errMessage } from "@/lib/api";
import { adminApi } from "@/lib/admin";

interface SessionInfo {
  source: string | null;
  has_tokens: boolean;
  user_id: string;
  error?: string;
}
interface Config {
  scraping_configured: boolean;
  session: SessionInfo;
  template_captured?: boolean;
  schedule_enabled: boolean;
  interval_hours: number;
  countries: string[];          // the FULL unified sweep scope (core + global)
  search_terms: string[];
  min_days_running: number;
  min_variants: number;
  max_per_country: number;
  global_enabled?: boolean;
  global_countries?: string[];  // subset of `countries` with the lower cap
  global_max_per_country?: number;
}
interface TopAd {
  advertiser: string;
  country: string;
  days_running: number;
  variants: number;
  score: number;
}
interface Stats {
  fetched: number;
  unique: number;
  kept: number;
  dropped_spam: number;
  dropped_low_perf: number;
  indexed: number;
  marked_inactive?: number;
  brands_deepdived?: number;
  catalog_indexed?: number;
  per_country: Record<string, number>;
  top: TopAd[];
}
interface Status {
  scraping_configured: boolean;
  session: SessionInfo;
  template_captured?: boolean;
  last_run: {
    status: string;
    started_at: string | null;
    finished_at: string | null;
    stats: Stats | null;
    alert?: string | null;
  };
}
interface Health {
  elasticsearch: { ok: boolean; status: string };
  postgres: { ok: boolean; status?: string };
  redis: { ok: boolean; status: string };
  facebook_session: { ok: boolean };
}

export default function AdminIngestionPage() {
  const { getToken } = useAuth();
  const [config, setConfig] = useState<Config | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [countries, setCountries] = useState("");
  const [terms, setTerms] = useState("");
  const [maxPer, setMaxPer] = useState<number | "">("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [cookie, setCookie] = useState("");
  const [savingCookie, setSavingCookie] = useState(false);
  const [cookieMsg, setCookieMsg] = useState("");
  const [curl, setCurl] = useState("");
  const [savingCurl, setSavingCurl] = useState(false);
  const [curlMsg, setCurlMsg] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadConfig = useCallback(async () => {
    try {
      const r = await authFetch(getToken, "/api/ingestion/config");
      if (!r.ok) throw new Error(await apiError(r));
      setConfig(await r.json());
    } catch (e) {
      setError(errMessage(e, "Cannot reach the API. Is the backend running on :8000?"));
    }
  }, [getToken]);

  const loadStatus = useCallback(async () => {
    try {
      const r = await authFetch(getToken, "/api/ingestion/status");
      const s: Status = await r.json();
      setStatus(s);
      if (s.last_run.status !== "running" && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      /* ignore transient poll errors */
    }
  }, [getToken]);

  useEffect(() => {
    loadConfig();
    loadStatus();
    adminApi.health(getToken).then(setHealth).catch(() => {});
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loadConfig, loadStatus, getToken]);

  const run = async () => {
    setStarting(true);
    setError("");
    try {
      const body: Record<string, unknown> = { wait: false };
      if (countries.trim()) body.countries = countries.split(",").map((c) => c.trim().toUpperCase()).filter(Boolean);
      if (terms.trim()) body.search_terms = terms.split(",").map((t) => t.trim()).filter(Boolean);
      if (maxPer !== "") body.max_per_country = Number(maxPer);

      const r = await authFetch(getToken, "/api/ingestion/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await r.json();
      if (!data.scraping_configured) {
        setError(data.note || "No Facebook session found.");
      }
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(loadStatus, 2500);
      setTimeout(loadStatus, 800);
    } catch {
      setError("Failed to start ingestion.");
    } finally {
      setStarting(false);
    }
  };

  const saveCookie = async () => {
    setSavingCookie(true);
    setCookieMsg("");
    try {
      const r = await authFetch(getToken, "/api/ingestion/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cookie }),
      });
      const data = await r.json();
      if (data.ok) {
        setCookieMsg(`Saved ✓ ${data.has_tokens ? "(tokens ok)" : "(no tokens — try again)"}`);
        setCookie("");
        loadConfig();
        loadStatus();
      } else {
        setCookieMsg(data.error || "Could not save cookie.");
      }
    } catch {
      setCookieMsg("Failed to reach the API.");
    } finally {
      setSavingCookie(false);
    }
  };

  const saveCurl = async () => {
    setSavingCurl(true);
    setCurlMsg("");
    try {
      const r = await authFetch(getToken, "/api/ingestion/search-template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ curl }),
      });
      const data = await r.json();
      if (data.ok) {
        setCurlMsg(`Saved ✓ (doc_id ${data.doc_id})`);
        setCurl("");
        loadConfig();
        loadStatus();
      } else {
        setCurlMsg(data.error || "Could not parse the request.");
      }
    } catch {
      setCurlMsg("Failed to reach the API.");
    } finally {
      setSavingCurl(false);
    }
  };

  const running = status?.last_run.status === "running";
  const stats = status?.last_run.stats;
  const configured = config?.scraping_configured;

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto">
      <h2 className="text-2xl font-black tracking-tight text-[#1d1d1f] mb-1 flex items-center gap-2">
        <Download className="w-6 h-6" /> Ad Ingestion
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        Pull the best-performing e-commerce ads from Meta&apos;s Ad Library —
        long-running and scaling winners only, spam filtered out.
      </p>

      {/* System health strip */}
      {health && (
        <div className="flex items-center gap-4 bg-white border border-[#e6e6e7] rounded-2xl px-4 py-3 mb-6 text-xs">
          <span className="flex items-center gap-1 font-medium text-gray-500">
            <Activity className="w-3.5 h-3.5" /> System
          </span>
          {[
            ["Elasticsearch", health.elasticsearch.ok],
            ["Postgres", health.postgres.ok],
            ["Redis", health.redis.ok],
            ["FB session", health.facebook_session.ok],
          ].map(([label, ok]) => (
            <span key={label as string} className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"}`} />
              {label}
            </span>
          ))}
        </div>
      )}

      {/* Dead-session / sweep alert */}
      {status?.last_run.alert && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-red-800">Ingestion needs attention</p>
            <p className="text-sm text-red-700 mt-0.5">{status.last_run.alert}</p>
          </div>
        </div>
      )}

      {/* Session status */}
      <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {configured ? (
              <CheckCircle2 className="w-5 h-5 text-green-600" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
            <div>
              <p className="text-sm font-medium text-gray-900">
                {configured ? "Facebook session active" : "No Facebook session"}
              </p>
              <p className="text-xs text-gray-500">
                {configured
                  ? `Auto-detected via ${config?.session.source}${config?.session.has_tokens ? " (tokens ok)" : " (no tokens)"}`
                  : "Log into facebook.com in your browser — the backend reads it automatically."}
              </p>
              {!configured && config?.session.error && (
                <p className="text-xs text-red-500 mt-1 font-mono break-all">{config.session.error}</p>
              )}
            </div>
          </div>
          <button
            onClick={() => { loadConfig(); loadStatus(); }}
            className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
        {config && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-xs">
              <Meta label="Schedule" value={config.schedule_enabled ? `every ${config.interval_hours}h, all markets` : "manual"} />
              <Meta label="Min days running" value={String(config.min_days_running)} />
              <Meta label="Min variants" value={String(config.min_variants)} />
              <Meta
                label="Max / country"
                value={
                  config.global_max_per_country
                    ? `${config.max_per_country} · 🌍 ${config.global_max_per_country}`
                    : String(config.max_per_country)
                }
              />
            </div>
            <div className="flex flex-wrap items-center gap-1.5 mt-3 text-xs">
              <span className="text-gray-400 mr-1">Sweep covers {config.countries.length} markets:</span>
              {config.countries.map((c) => {
                const isGlobal = config.global_countries?.includes(c);
                return (
                  <span
                    key={c}
                    title={isGlobal ? "Global trend market (lower per-country cap)" : "Core market"}
                    className={`px-2 py-0.5 rounded-full font-semibold ${
                      isGlobal ? "bg-indigo-50 text-indigo-600" : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {isGlobal ? "🌍 " : ""}{c}
                  </span>
                );
              })}
            </div>
          </>
        )}

        {!configured && (
          <div className="mt-4 pt-4 border-t border-gray-100">
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Paste your Facebook cookie (once)
            </label>
            <p className="text-xs text-gray-400 mb-2">
              Opera GX/Chrome encrypt cookies, so paste once here. In a logged-in
              facebook.com tab: DevTools → Network → click any request → Headers →
              copy the <span className="font-mono">Cookie</span> value (must include
              <span className="font-mono"> c_user</span> and <span className="font-mono">xs</span>).
              Stored locally; lasts months.
            </p>
            <textarea
              value={cookie}
              onChange={(e) => setCookie(e.target.value)}
              rows={3}
              placeholder="c_user=...; xs=...; datr=...; ..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs font-mono"
            />
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={saveCookie}
                disabled={savingCookie || !cookie.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white text-sm rounded-lg hover:bg-gray-700 disabled:opacity-50"
              >
                {savingCookie ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Save session
              </button>
              {cookieMsg && <span className="text-xs text-gray-600">{cookieMsg}</span>}
            </div>
          </div>
        )}
      </div>

      {/* Capture search request (GraphQL endpoint) */}
      {configured && !config?.template_captured && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-6">
          <p className="text-sm font-medium text-amber-900 mb-1">One more step: capture the search request</p>
          <p className="text-xs text-amber-800 mb-2">
            Meta&apos;s search API uses a rotating ID we can&apos;t guess, so capture your
            browser&apos;s real request once. On <span className="font-mono">facebook.com/ads/library</span>:
            run any search → DevTools (F12) → <b>Network</b> → filter <span className="font-mono">graphql</span> →
            click the request whose response has ads → right-click → <b>Copy → Copy as cURL</b> → paste below.
            Parsed locally; your cookie stays on your machine.
          </p>
          <textarea
            value={curl}
            onChange={(e) => setCurl(e.target.value)}
            rows={3}
            placeholder="curl 'https://www.facebook.com/api/graphql/' -H '...' --data-raw '...doc_id=...&variables=...'"
            className="w-full px-3 py-2 border border-amber-300 rounded-lg text-xs font-mono"
          />
          <div className="flex items-center gap-3 mt-2">
            <button
              onClick={saveCurl}
              disabled={savingCurl || !curl.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-amber-600 text-white text-sm rounded-lg hover:bg-amber-500 disabled:opacity-50"
            >
              {savingCurl ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Save search request
            </button>
            {curlMsg && <span className="text-xs text-amber-900">{curlMsg}</span>}
          </div>
        </div>
      )}
      {configured && config?.template_captured && (
        <p className="text-xs text-green-600 mb-4 flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5" /> Search request captured — ready to ingest.
        </p>
      )}

      {/* Run controls */}
      <div className="bg-white border border-[#e6e6e7] rounded-2xl p-6 mb-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-1">
            <label className="block text-xs font-medium text-gray-500 mb-1">Countries (comma)</label>
            <input
              value={countries}
              onChange={(e) => setCountries(e.target.value)}
              placeholder={config?.countries.join(", ") || "TN, MA, EG"}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div className="md:col-span-1">
            <label className="block text-xs font-medium text-gray-500 mb-1">Search terms (comma)</label>
            <input
              value={terms}
              onChange={(e) => setTerms(e.target.value)}
              placeholder="livraison gratuite, promo, تخفيضات"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Max / country</label>
            <input
              type="number"
              value={maxPer}
              onChange={(e) => setMaxPer(e.target.value === "" ? "" : Number(e.target.value))}
              placeholder={String(config?.max_per_country ?? 40)}
              className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm"
            />
          </div>
        </div>
        <p className="text-xs text-gray-400">
          Leave blank to sweep every market — MENA core + 🌍 global trends — in one run.
        </p>
        <button
          onClick={run}
          disabled={starting || running}
          className="btn-holo w-full py-3 text-sm disabled:opacity-50"
        >
          {starting || running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {running ? "Ingestion running…" : starting ? "Starting…" : "Run ingestion"}
        </button>
        {error && <p className="text-sm text-amber-600">{error}</p>}
      </div>

      {/* Results */}
      {status && status.last_run.status !== "never_run" && (
        <div className="bg-white border border-[#e6e6e7] rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">
              Last run — <span className={running ? "text-blue-600" : "text-green-600"}>{status.last_run.status}</span>
            </h3>
            {status.last_run.finished_at && (
              <span className="text-xs text-gray-400">{new Date(status.last_run.finished_at).toLocaleString()}</span>
            )}
          </div>

          {stats ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-9 gap-3 mb-6">
                <Stat label="Fetched" value={stats.fetched} />
                <Stat label="Unique" value={stats.unique} />
                <Stat label="Kept" value={stats.kept} highlight />
                <Stat label="Spam cut" value={stats.dropped_spam} />
                <Stat label="Low-perf cut" value={stats.dropped_low_perf} />
                <Stat label="Indexed" value={stats.indexed} highlight />
                <Stat label="Gone stale" value={stats.marked_inactive ?? 0} />
                <Stat label="Brands dived" value={stats.brands_deepdived ?? 0} />
                <Stat label="Catalog added" value={stats.catalog_indexed ?? 0} />
              </div>

              {stats.per_country && Object.keys(stats.per_country).length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5 mb-6 text-xs">
                  <span className="text-gray-400 mr-1">Kept per market:</span>
                  {Object.entries(stats.per_country)
                    .sort(([, a], [, b]) => b - a)
                    .map(([c, n]) => (
                      <span key={c} className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 font-semibold">
                        {c} {n}
                      </span>
                    ))}
                </div>
              )}

              {stats.top.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-gray-500 uppercase mb-2">Top winners</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                          <th className="py-2">Advertiser</th>
                          <th className="py-2">Country</th>
                          <th className="py-2">Days</th>
                          <th className="py-2">Variants</th>
                          <th className="py-2">Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.top.map((t, i) => (
                          <tr key={i} className="border-b border-gray-50">
                            <td className="py-2 font-medium text-gray-800">{t.advertiser}</td>
                            <td className="py-2 text-gray-600">{t.country}</td>
                            <td className="py-2 text-gray-600">{t.days_running}</td>
                            <td className="py-2 text-gray-600">{t.variants}</td>
                            <td className="py-2 text-gray-900 font-semibold">{t.score}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-500 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Sweeping the Ad Library…
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-lg p-3 text-center ${highlight ? "bg-blue-50" : "bg-gray-50"}`}>
      <p className={`text-xl font-bold ${highlight ? "text-blue-700" : "text-gray-900"}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg px-3 py-2">
      <p className="text-gray-400">{label}</p>
      <p className="text-gray-800 font-medium">{value}</p>
    </div>
  );
}
