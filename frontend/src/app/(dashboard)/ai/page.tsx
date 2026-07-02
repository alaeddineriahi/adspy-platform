"use client";

import { useState } from "react";
import Link from "next/link";
import { Zap, Loader2, Film, Copy, CheckCheck } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { authFetch, apiError, errMessage } from "@/lib/api";
import { useUsage } from "@/components/UsageProvider";

interface Hook {
  type: string;
  text: string;
}
interface Scene {
  timestamp: string;
  beat: string;
  visual: string;
  on_screen_text: string;
  voiceover: string;
}
interface VideoScript {
  concept?: string;
  hooks?: Hook[];
  scenes?: Scene[];
  cta?: string;
  caption?: string;
  music_vibe?: string;
  tips?: string[];
}

export default function AIToolsPage() {
  const { getToken } = useAuth();
  const { refresh: refreshUsage } = useUsage();
  const [outOfCredits, setOutOfCredits] = useState(false);
  const [product, setProduct] = useState("");
  const [audience, setAudience] = useState("");
  const [platform, setPlatform] = useState("tiktok");
  const [language, setLanguage] = useState("en");
  const [duration, setDuration] = useState(30);
  const [tone, setTone] = useState("energetic direct-response");
  const [loading, setLoading] = useState(false);
  const [script, setScript] = useState<VideoScript | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const generate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setOutOfCredits(false);
    setScript(null);
    try {
      const res = await authFetch(getToken, "/api/ai/generate-video-script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product, audience, platform, language, duration, tone }),
      });
      if (res.status === 402) setOutOfCredits(true);
      if (!res.ok) throw new Error(await apiError(res));
      setScript(await res.json());
      refreshUsage(); // keep the sidebar credit meter honest
    } catch (err) {
      setError(errMessage(err, "Generation failed"));
    } finally {
      setLoading(false);
    }
  };

  const copyScript = () => {
    if (!script) return;
    const text = [
      script.concept ? `CONCEPT: ${script.concept}` : "",
      "",
      "HOOKS:",
      ...(script.hooks || []).map((h) => `- (${h.type}) ${h.text}`),
      "",
      "SCRIPT:",
      ...(script.scenes || []).map(
        (s) =>
          `[${s.timestamp}] ${s.beat}\n  Visual: ${s.visual}\n  On-screen: ${s.on_screen_text}\n  VO: ${s.voiceover}`
      ),
      "",
      `CTA: ${script.cta || ""}`,
      script.caption ? `\nCAPTION: ${script.caption}` : "",
    ].join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold text-gray-900 mb-1 flex items-center gap-2">
        <Film className="w-6 h-6" /> AI Video Script Generator
      </h2>
      <p className="text-sm text-gray-500 mb-6">
        High-converting short-form video scripts: scroll-stopping hooks, scene-by-scene
        breakdown, and a CTA — built for Meta Reels & TikTok.
      </p>

      <form onSubmit={generate} className="space-y-4 bg-white border border-gray-200 rounded-xl p-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Product / Service</label>
          <input
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            required
            placeholder="e.g. Organic argan oil skincare serum"
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target audience</label>
          <input
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            required
            placeholder="e.g. Women 25-40 in Tunisia interested in natural beauty"
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm"
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Platform</label>
            <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white">
              <option value="tiktok">TikTok</option>
              <option value="meta">Meta Reels</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Language</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)} className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white">
              <option value="en">English</option>
              <option value="fr">Français</option>
              <option value="ar">العربية</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Duration (s)</label>
            <select value={duration} onChange={(e) => setDuration(Number(e.target.value))} className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white">
              <option value={15}>15</option>
              <option value={30}>30</option>
              <option value={45}>45</option>
              <option value={60}>60</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Tone</label>
            <select value={tone} onChange={(e) => setTone(e.target.value)} className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm bg-white">
              <option value="energetic direct-response">Energetic</option>
              <option value="luxury / premium">Luxury</option>
              <option value="friendly and relatable">Friendly</option>
              <option value="bold and contrarian">Bold</option>
            </select>
          </div>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="btn-holo w-full py-3 text-sm disabled:opacity-50"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
          {loading ? "Writing your script..." : "Generate video script"}
        </button>
      </form>

      {error && (
        <div className="mt-4 flex items-center justify-between gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          <p className="text-sm text-red-700">{error}</p>
          {outOfCredits && (
            <Link
              href="/pricing"
              className="btn-holo shrink-0 px-4 py-2 text-sm"
            >
              Upgrade
            </Link>
          )}
        </div>
      )}

      {script && (
        <div className="mt-6 space-y-6">
          {/* Concept + copy button */}
          <div className="flex items-start justify-between gap-4">
            {script.concept && (
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex-1">
                <span className="text-xs font-semibold text-blue-600 uppercase">Concept</span>
                <p className="text-sm text-blue-900 mt-1">{script.concept}</p>
              </div>
            )}
            <button
              onClick={copyScript}
              className="shrink-0 flex items-center gap-2 px-4 py-2.5 border border-gray-300 rounded-lg text-sm hover:bg-gray-50"
            >
              {copied ? <CheckCheck className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              {copied ? "Copied" : "Copy script"}
            </button>
          </div>

          {/* Hooks */}
          {script.hooks && script.hooks.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Hook options</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {script.hooks.map((h, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-lg p-4">
                    <span className="text-xs font-medium text-gray-400 uppercase">{h.type}</span>
                    <p className="text-sm text-gray-900 mt-1.5">{h.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Scenes */}
          {script.scenes && script.scenes.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Scene-by-scene</h3>
              <div className="space-y-3">
                {script.scenes.map((s, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 flex gap-4">
                    <div className="shrink-0 w-24">
                      <span className="text-xs font-mono text-gray-500">{s.timestamp}</span>
                      <span className="block mt-1 text-xs font-semibold text-blue-600">{s.beat}</span>
                    </div>
                    <div className="flex-1 space-y-1.5">
                      <p className="text-sm text-gray-900">🎙️ {s.voiceover}</p>
                      {s.on_screen_text && (
                        <p className="text-xs text-gray-600">
                          <span className="font-medium">On-screen:</span> {s.on_screen_text}
                        </p>
                      )}
                      {s.visual && (
                        <p className="text-xs text-gray-500">
                          <span className="font-medium">Visual:</span> {s.visual}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* CTA + meta */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {script.cta && (
              <div className="bg-gray-900 text-white rounded-xl p-4">
                <span className="text-xs font-semibold text-gray-400 uppercase">Call to action</span>
                <p className="text-sm mt-1">{script.cta}</p>
              </div>
            )}
            {script.caption && (
              <div className="bg-white border border-gray-200 rounded-xl p-4">
                <span className="text-xs font-semibold text-gray-400 uppercase">Caption</span>
                <p className="text-sm text-gray-800 mt-1">{script.caption}</p>
              </div>
            )}
          </div>

          {/* Tips */}
          {script.tips && script.tips.length > 0 && (
            <div className="bg-amber-50 border border-amber-100 rounded-xl p-4">
              <span className="text-xs font-semibold text-amber-700 uppercase">Production tips</span>
              <ul className="mt-2 space-y-1">
                {script.tips.map((t, i) => (
                  <li key={i} className="text-sm text-amber-900">• {t}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
