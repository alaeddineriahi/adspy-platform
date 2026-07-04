"use client";

import { useState } from "react";

/**
 * Fenki — the AdSpy mascot (white fennec, holo-gradient ears, red chachia).
 *
 * Assets live in /public/mascot/. The renders sit on an OFF-white background
 * (~#f3f3f3, no alpha), so three layers make them seamless on the page:
 *   1. brightness boost clips the near-white bg to pure white,
 *   2. mix-blend-multiply makes pure white invisible on the page,
 *   3. an edge mask + bottom fade melt the frame borders (and hide the
 *      gradient bar baked into the video's floor) into the page.
 *
 * - default: autoplaying idle loop (webm -> mp4), poster = still
 * - prefers-reduced-motion: the still only (Tailwind motion-reduce)
 * - video error (codec/404): falls back to the still
 * - Edge/Chrome hover media overlays (PiP etc.) are suppressed.
 *
 * Expression stills (hot/thinking/empty/celebrate) plug in via `pose` once
 * generated — missing PNGs gracefully fall back to the hero still.
 */
export type MascotPose = "hero" | "hot" | "thinking" | "empty" | "celebrate";

// One generous elliptical mask fades every edge of the frame — hides the
// video's hard border AND the gradient bar baked into its floor, while the
// character (centered, slightly high) stays fully opaque.
const EDGE_MASK = {
  maskImage: "radial-gradient(ellipse 72% 68% at 50% 42%, black 58%, transparent 92%)",
  WebkitMaskImage: "radial-gradient(ellipse 72% 68% at 50% 42%, black 58%, transparent 92%)",
} as React.CSSProperties;

const MELT = "mix-blend-multiply [filter:brightness(1.06)]";

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
      style={{ width: size, height: size * 0.82 }}
    >
      <div className="absolute inset-0" style={EDGE_MASK}>
        {showVideo && (
          <video
            className={`w-full h-full object-cover motion-reduce:hidden ${MELT}`}
            autoPlay
            muted
            loop
            playsInline
            disablePictureInPicture
            controlsList="nodownload noplaybackrate noremoteplayback"
            poster="/mascot/fenki-hero.webp"
            aria-hidden
            onError={() => setVideoOk(false)}
            onContextMenu={(e) => e.preventDefault()}
          >
            <source src="/mascot/fenki-idle-loop.webm" type="video/webm" />
            <source src="/mascot/fenki-idle-loop.mp4" type="video/mp4" />
          </video>
        )}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={still}
          alt="Fenki, the AdSpy fennec"
          className={`w-full h-full object-cover ${MELT} ${
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
    </div>
  );
}
