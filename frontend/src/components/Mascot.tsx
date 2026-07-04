"use client";

import { useState } from "react";

/**
 * Fenki — the AdSpy mascot (white fennec, holo-gradient ears, red chachia).
 *
 * Assets live in /public/mascot/. The renders sit on a WHITE background (no
 * alpha), so `mix-blend-multiply` melts them into the near-white (#fbfbfb)
 * page: white pixels become invisible, the character stays intact.
 *
 * - default: autoplaying idle loop (webm first, mp4 fallback), poster = still
 * - prefers-reduced-motion: the still image only (Tailwind motion-reduce)
 * - video error (codec/404): falls back to the still
 *
 * Expression stills (hot/thinking/empty/celebrate) plug in via `pose` once
 * generated — they're optional and default to the hero still if missing.
 */
export type MascotPose = "hero" | "hot" | "thinking" | "empty" | "celebrate";

export function Mascot({
  size = 240,
  pose = "hero",
  animated = true,
  className = "",
}: {
  size?: number;
  pose?: MascotPose;
  animated?: boolean;
  className?: string;
}) {
  const [videoOk, setVideoOk] = useState(true);
  const still = pose === "hero" ? "/mascot/fenki-hero.webp" : `/mascot/fenki-${pose}.png`;
  const showVideo = animated && pose === "hero" && videoOk;

  return (
    <div
      className={`relative mx-auto select-none pointer-events-none ${className}`}
      style={{ width: size, height: size }}
    >
      {showVideo && (
        <video
          className="w-full h-full object-cover mix-blend-multiply motion-reduce:hidden"
          autoPlay
          muted
          loop
          playsInline
          poster="/mascot/fenki-hero.webp"
          aria-hidden
          onError={() => setVideoOk(false)}
        >
          <source src="/mascot/fenki-idle-loop.webm" type="video/webm" />
          <source src="/mascot/fenki-idle-loop.mp4" type="video/mp4" />
        </video>
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={still}
        alt="Fenki, the AdSpy fennec"
        className={`w-full h-full object-cover mix-blend-multiply ${
          showVideo ? "hidden motion-reduce:block" : "block"
        }`}
        onError={(e) => {
          // missing expression PNG → fall back to the hero still
          if (!e.currentTarget.src.endsWith("fenki-hero.webp")) {
            e.currentTarget.src = "/mascot/fenki-hero.webp";
          }
        }}
      />
    </div>
  );
}
