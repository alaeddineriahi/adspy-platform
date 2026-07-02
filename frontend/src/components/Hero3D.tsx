import { TrendingUp, Clock } from "lucide-react";
import { CSSProperties } from "react";

/**
 * 3D rotating ring of stylized "spied ad" cards — pure CSS perspective
 * (the same technique Holo uses for its hero carousel), zero JS and no
 * WebGL payload. Pauses on hover; disabled by prefers-reduced-motion.
 */

const CARDS = [
  { flag: "🇹🇳", niche: "Parfum", days: 214, score: 96, from: "#3e86c6", to: "#a666aa" },
  { flag: "🇲🇦", niche: "Hijab mode", days: 187, score: 93, from: "#a666aa", to: "#ec4492" },
  { flag: "🇸🇦", niche: "Skincare", days: 609, score: 99, from: "#ec4492", to: "#ee4454" },
  { flag: "🇪🇬", niche: "Gadget cuisine", days: 96, score: 88, from: "#ee4454", to: "#f05427" },
  { flag: "🇩🇿", niche: "Montres", days: 143, score: 91, from: "#f05427", to: "#3e86c6" },
  { flag: "🇦🇪", niche: "Compléments", days: 178, score: 94, from: "#3e86c6", to: "#ec4492" },
  { flag: "🇹🇳", niche: "Bébé & kids", days: 121, score: 87, from: "#a666aa", to: "#ee4454" },
  { flag: "🇲🇦", niche: "Sneakers", days: 156, score: 90, from: "#ec4492", to: "#f05427" },
];

export function Hero3D() {
  return (
    <div className="scene3d flex justify-center overflow-hidden py-10 select-none" aria-hidden="true">
      <div
        className="ring3d h-[240px] w-[170px]"
        style={{ "--radius": "340px" } as CSSProperties}
      >
        {CARDS.map((c, i) => (
          <div
            key={i}
            className="ring-card h-[240px] w-[170px]"
            style={{ "--i": `${(360 / CARDS.length) * i}deg` } as CSSProperties}
          >
            <div className="h-full w-full rounded-2xl bg-white border border-[#e6e6e7] shadow-xl shadow-gray-200/60 overflow-hidden flex flex-col">
              {/* Fake creative */}
              <div
                className="h-[120px] relative flex items-end p-2.5"
                style={{ background: `linear-gradient(135deg, ${c.from}22, ${c.to}33)` }}
              >
                <span className="absolute top-2.5 left-2.5 text-lg">{c.flag}</span>
                <span
                  className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold text-white"
                  style={{ background: `linear-gradient(90deg, ${c.from}, ${c.to})` }}
                >
                  <TrendingUp className="w-2.5 h-2.5" /> {c.score}
                </span>
              </div>
              {/* Fake copy lines */}
              <div className="p-3 flex-1 flex flex-col gap-1.5">
                <p className="text-[11px] font-bold text-[#1d1d1f]">{c.niche}</p>
                <div className="h-1.5 rounded-full bg-gray-100 w-full" />
                <div className="h-1.5 rounded-full bg-gray-100 w-3/4" />
                <div className="mt-auto flex items-center gap-1 text-[10px] text-[#6e6e73]">
                  <Clock className="w-2.5 h-2.5" /> {c.days}d running
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
