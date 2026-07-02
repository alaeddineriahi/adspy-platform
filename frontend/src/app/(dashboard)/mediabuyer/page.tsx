"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Link from "next/link";
import { Megaphone, Send, Loader2, Sparkles, RotateCcw, SlidersHorizontal, Check } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { authFetch, apiError, API_URL } from "@/lib/api";
import { useUsage } from "@/components/UsageProvider";

const PROFILE_KEY = "adspy_buyer_profile";
const CHAT_KEY = "adspy_buyer_chat";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

interface Profile {
  country: string;
  budget: string;
  creatives_count: string;
  creative_types: string[];
  experience: string;
  platform: string;
  product: string;
}

const EMPTY_PROFILE: Profile = {
  country: "",
  budget: "",
  creatives_count: "",
  creative_types: [],
  experience: "",
  platform: "meta",
  product: "",
};

const COUNTRIES: [string, string][] = [
  ["TN", "Tunisia"], ["DZ", "Algeria"], ["MA", "Morocco"], ["EG", "Egypt"],
  ["SA", "Saudi Arabia"], ["AE", "UAE"], ["KW", "Kuwait"], ["QA", "Qatar"],
];
const CURRENCY: Record<string, string> = {
  TN: "TND", DZ: "DZD", MA: "MAD", EG: "EGP", SA: "SAR", AE: "AED", KW: "KWD", QA: "QAR",
};
const CREATIVE_TYPES = ["None yet", "Product images", "UGC video", "Product demo video", "Carousel"];
const EXPERIENCE: [string, string][] = [
  ["none", "Never run ads"],
  ["beginner", "Ran a few"],
  ["intermediate", "Comfortable"],
];

const STARTERS = [
  "I'm new to ads — where do I start?",
  "Is my budget enough to test this product?",
  "What creatives do I need, and how many?",
  "Build my first campaign plan step by step",
];

// Lightweight markdown-ish renderer (bold, bullets, headings) — no extra deps.
function Rich({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const bullet = /^\s*[-*]\s+/.test(line);
        const heading = /^#{1,6}\s+/.test(line);
        const clean = line.replace(/^\s*[-*]\s+/, "").replace(/^#{1,6}\s+/, "");
        if (!clean.trim()) return <div key={i} className="h-2" />;
        const content = <Inline text={clean} />;
        if (heading)
          return (
            <p key={i} className="font-semibold text-gray-900 mt-2">
              {content}
            </p>
          );
        if (bullet)
          return (
            <div key={i} className="flex gap-2">
              <span className="text-gray-400 mt-0.5">•</span>
              <span className="flex-1">{content}</span>
            </div>
          );
        return <p key={i}>{content}</p>;
      })}
    </div>
  );
}

function Inline({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((p, i) =>
        /^\*\*[^*]+\*\*$/.test(p) ? (
          <strong key={i} className="font-semibold text-gray-900">
            {p.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </>
  );
}

function cleanProfile(p: Profile) {
  const out: Record<string, unknown> = {};
  if (p.country) {
    out.country = p.country;
    out.currency = CURRENCY[p.country];
  }
  if (p.budget) out.budget = Number(p.budget);
  if (p.creatives_count !== "") out.creatives_count = Number(p.creatives_count);
  if (p.creative_types.length) out.creative_types = p.creative_types;
  if (p.experience) out.experience = p.experience;
  if (p.platform) out.platform = p.platform;
  if (p.product) out.product = p.product;
  return Object.keys(out).length ? out : undefined;
}

function profileSummary(p: Profile): string {
  const bits: string[] = [];
  const c = COUNTRIES.find(([code]) => code === p.country);
  if (c) bits.push(c[1]);
  if (p.budget) bits.push(`${p.budget} ${CURRENCY[p.country] || ""}/day`.trim());
  if (p.creatives_count !== "") bits.push(`${p.creatives_count} creatives`);
  const exp = EXPERIENCE.find(([v]) => v === p.experience);
  if (exp) bits.push(exp[1].toLowerCase());
  return bits.join(" · ");
}

export default function MediaBuyerPage() {
  const { getToken } = useAuth();
  const { refresh: refreshUsage } = useUsage();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [outOfCredits, setOutOfCredits] = useState(false);
  const [adId, setAdId] = useState<string | null>(null);
  const [adLabel, setAdLabel] = useState<string>("");
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [showSetup, setShowSetup] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load saved profile + previous conversation + optional spied-ad context on mount.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(PROFILE_KEY);
      if (saved) setProfile({ ...EMPTY_PROFILE, ...JSON.parse(saved) });
      else setShowSetup(true); // first visit: prompt them to fill it
    } catch {}
    try {
      const chat = localStorage.getItem(CHAT_KEY);
      if (chat) {
        const parsed = JSON.parse(chat);
        if (Array.isArray(parsed)) setMessages(parsed);
      }
    } catch {}
    setLoaded(true);

    const id = new URLSearchParams(window.location.search).get("ad");
    if (id) {
      setAdId(id);
      fetch(`${API_URL}/api/creatives/${id}`)
        .then((r) => (r.ok ? r.json() : null))
        .then((ad) => {
          if (ad) {
            setAdLabel(`${ad.advertiser_name} · ${ad.country} · ${ad.days_running}d`);
            setProfile((p) => (p.product ? p : { ...p, product: ad.advertiser_name || p.product }));
          }
        })
        .catch(() => {});
    }
  }, []);

  // Persist profile whenever it changes (after initial load).
  useEffect(() => {
    if (loaded) {
      try {
        localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
      } catch {}
    }
  }, [profile, loaded]);

  // Persist the conversation once each reply finishes (not on every token).
  useEffect(() => {
    if (!loaded || streaming) return;
    try {
      if (messages.length) localStorage.setItem(CHAT_KEY, JSON.stringify(messages.slice(-40)));
      else localStorage.removeItem(CHAT_KEY);
    } catch {}
  }, [messages, streaming, loaded]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const setField = (k: keyof Profile, v: string) => setProfile((p) => ({ ...p, [k]: v }));
  const toggleType = (t: string) =>
    setProfile((p) => ({
      ...p,
      creative_types: p.creative_types.includes(t)
        ? p.creative_types.filter((x) => x !== t)
        : [...p.creative_types, t],
    }));

  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q || streaming) return;
      const history = [...messages, { role: "user", content: q } as Msg];
      setMessages([...history, { role: "assistant", content: "" }]);
      setInput("");
      setStreaming(true);
      setOutOfCredits(false);
      try {
        const res = await authFetch(getToken, "/api/mediabuyer/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: history, ad_id: adId, profile: cleanProfile(profile) }),
        });
        if (res.status === 402) setOutOfCredits(true);
        if (!res.ok || !res.body) throw new Error(await apiError(res));
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let acc = "";
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          acc += decoder.decode(value, { stream: true });
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { role: "assistant", content: acc };
            return next;
          });
        }
        refreshUsage(); // sidebar meter reflects the credit just spent
      } catch (err: any) {
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = {
            role: "assistant",
            content: `⚠️ ${err.message || "Something went wrong. Is the backend running?"}`,
          };
          return next;
        });
      } finally {
        setStreaming(false);
      }
    },
    [messages, streaming, adId, profile, getToken, refreshUsage]
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const empty = messages.length === 0;
  const summary = profileSummary(profile);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-8 pt-6 pb-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Megaphone className="w-6 h-6" /> Media Buyer
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              A senior media buyer that gives you the honest truth — tailored to your budget, market and
              creatives. Advisory only for now (live launching is on the roadmap).
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSetup((s) => !s)}
              className="flex items-center gap-1.5 text-sm text-gray-700 border border-gray-200 hover:border-gray-900 px-3 py-1.5 rounded-lg"
            >
              <SlidersHorizontal className="w-4 h-4" /> Your setup
            </button>
            {!empty && (
              <button
                onClick={() => setMessages([])}
                className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 px-3 py-1.5 rounded-lg hover:bg-gray-100"
              >
                <RotateCcw className="w-4 h-4" /> New chat
              </button>
            )}
          </div>
        </div>

        {adLabel && (
          <div className="mt-3 inline-flex items-center gap-2 text-xs bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-lg px-3 py-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            Planning around a spied winner: <span className="font-semibold">{adLabel}</span>
          </div>
        )}
        {!showSetup && summary && (
          <div className="mt-3 text-xs text-gray-500">
            Advice tailored to: <span className="font-medium text-gray-700">{summary}</span>
          </div>
        )}

        {/* Setup panel */}
        {showSetup && (
          <div className="mt-4 bg-gray-50 border border-gray-200 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-3">
              Fill this once so your media buyer tailors every answer to your situation. Saved on this device.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Country</label>
                <select
                  value={profile.country}
                  onChange={(e) => setField("country", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  <option value="">Select…</option>
                  {COUNTRIES.map(([code, name]) => (
                    <option key={code} value={code}>{name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Daily budget {profile.country ? `(${CURRENCY[profile.country]})` : ""}
                </label>
                <input
                  type="number"
                  min={0}
                  value={profile.budget}
                  onChange={(e) => setField("budget", e.target.value)}
                  placeholder="e.g. 30"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1"># Creatives ready</label>
                <input
                  type="number"
                  min={0}
                  value={profile.creatives_count}
                  onChange={(e) => setField("creatives_count", e.target.value)}
                  placeholder="e.g. 2"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Experience</label>
                <select
                  value={profile.experience}
                  onChange={(e) => setField("experience", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  <option value="">Select…</option>
                  {EXPERIENCE.map(([v, label]) => (
                    <option key={v} value={v}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Product / niche (optional)</label>
                <input
                  value={profile.product}
                  onChange={(e) => setField("product", e.target.value)}
                  placeholder="e.g. argan oil serum"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Platform</label>
                <select
                  value={profile.platform}
                  onChange={(e) => setField("platform", e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white"
                >
                  <option value="meta">Meta (FB/IG)</option>
                  <option value="tiktok">TikTok</option>
                </select>
              </div>
              <div className="flex items-end">
                <button
                  onClick={() => setShowSetup(false)}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-900 text-white rounded-lg text-sm hover:bg-gray-800"
                >
                  <Check className="w-4 h-4" /> Done
                </button>
              </div>
            </div>
            <div className="mt-3">
              <label className="block text-xs font-medium text-gray-600 mb-1.5">Creative types you have</label>
              <div className="flex flex-wrap gap-2">
                {CREATIVE_TYPES.map((t) => {
                  const on = profile.creative_types.includes(t);
                  return (
                    <button
                      key={t}
                      onClick={() => toggleType(t)}
                      className={`text-xs px-3 py-1.5 rounded-full border transition ${
                        on
                          ? "bg-gray-900 text-white border-gray-900"
                          : "bg-white text-gray-600 border-gray-300 hover:border-gray-900"
                      }`}
                    >
                      {t}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto px-8 py-6">
        <div className="max-w-3xl mx-auto">
          {empty ? (
            <div className="text-center py-12">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-gray-900 flex items-center justify-center mb-4">
                <Megaphone className="w-7 h-7 text-white" />
              </div>
              <p className="text-lg font-medium text-gray-900">Ask your media buyer anything</p>
              <p className="text-sm text-gray-500 mt-1 mb-6">
                Straight answers on budgets, targeting, creatives and scaling — no fluff, tailored to you.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="text-sm text-gray-700 border border-gray-200 rounded-xl px-4 py-3 hover:border-gray-900 hover:bg-gray-50 transition"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              {messages.map((m, i) => (
                <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <div
                    className={
                      m.role === "user"
                        ? "max-w-[80%] bg-gray-900 text-white rounded-2xl rounded-br-sm px-4 py-2.5 text-sm whitespace-pre-wrap"
                        : "max-w-[85%] bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-gray-700 leading-relaxed"
                    }
                  >
                    {m.role === "assistant" ? (
                      m.content ? (
                        <Rich text={m.content} />
                      ) : (
                        <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                      )
                    ) : (
                      m.content
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Composer */}
      <div className="border-t border-gray-200 bg-white px-8 py-4">
        {outOfCredits && (
          <div className="max-w-3xl mx-auto mb-3 flex items-center justify-between gap-3 bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
            <p className="text-sm text-blue-900">
              You're out of AI credits this month — upgrade to keep the conversation going.
            </p>
            <Link
              href="/pricing"
              className="shrink-0 text-sm font-semibold bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-500"
            >
              See plans
            </Link>
          </div>
        )}
        <div className="max-w-3xl mx-auto flex items-end gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Ask about budgets, targeting, scaling…  (Enter to send, Shift+Enter for newline)"
            className="flex-1 resize-none max-h-40 px-4 py-3 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={() => send(input)}
            disabled={streaming || !input.trim()}
            className="shrink-0 flex items-center justify-center w-11 h-11 bg-gray-900 text-white rounded-xl hover:bg-gray-800 disabled:opacity-40"
          >
            {streaming ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
