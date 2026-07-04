"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Fenki — the AdSpy mascot (white fennec, holo-gradient ears, red chachia).
 *
 * Assets live in /public/mascot/ on an OFF-white (~#f3f3f3) background, no
 * alpha. The seamless look = brightness clip (bg → pure white) + multiply
 * blend (pure white → invisible) + an elliptical edge mask.
 *
 * WHY A CANVAS: applying those treatments straight to a <video> works only
 * until playback starts — Windows browsers promote playing videos to a
 * hardware overlay that IGNORES CSS blend modes/filters/masks (the "fixed
 * for an instant, then the box came back" bug). So a hidden <video> only
 * decodes, a <canvas> mirrors its frames (cropping the gradient bar baked
 * into the video's floor at the source), and the CSS lives on the canvas —
 * a normal element the compositor can never bypass.
 *
 * - prefers-reduced-motion / video error → the still image (same treatments;
 *   images never get overlay-promoted, so CSS is reliable there)
 * - expression poses (hot/thinking/empty/celebrate) via `pose`; missing
 *   PNGs fall back to the hero still.
 */
export type MascotPose = "hero" | "hot" | "thinking" | "empty" | "celebrate";

// Fade all edges; swallow any residual frame border.
const EDGE_MASK = {
  maskImage: "radial-gradient(ellipse 72% 68% at 50% 44%, black 58%, transparent 92%)",
  WebkitMaskImage: "radial-gradient(ellipse 72% 68% at 50% 44%, black 58%, transparent 92%)",
} as React.CSSProperties;

const MELT = "mix-blend-multiply [filter:brightness(1.06)]";

// Bottom slice of the video frame to discard (the baked-in gradient bar).
const CROP_BOTTOM = 0.14;

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
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [playing, setPlaying] = useState(false);
  const [videoOk, setVideoOk] = useState(true);

  const still = pose === "hero" ? "/mascot/fenki-hero.webp" : `/mascot/fenki-${pose}.png`;
  const wantVideo = animated && pose === "hero" && videoOk;

  useEffect(() => {
    if (!wantVideo) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    let raf = 0;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      if (video.readyState >= 2 && video.videoWidth) {
        const sw = video.videoWidth;
        const sh = Math.floor(video.videoHeight * (1 - CROP_BOTTOM));
        if (canvas.width !== sw || canvas.height !== sh) {
          canvas.width = sw;
          canvas.height = sh;
        }
        ctx.drawImage(video, 0, 0, sw, sh, 0, 0, sw, sh);
      }
      raf = requestAnimationFrame(draw);
    };

    const onPlaying = () => {
      setPlaying(true);
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(draw);
    };
    const onError = () => setVideoOk(false);

    video.addEventListener("playing", onPlaying);
    video.addEventListener("error", onError);
    video.play().catch(() => setVideoOk(false));

    return () => {
      cancelAnimationFrame(raf);
      video.removeEventListener("playing", onPlaying);
      video.removeEventListener("error", onError);
      video.pause();
    };
  }, [wantVideo]);

  return (
    <div
      className={`relative mx-auto select-none pointer-events-none ${className}`}
      style={{ width: size, height: size * 0.82 }}
    >
      {/* decoder only — never visible, never overlay-promoted into view */}
      {wantVideo && (
        <video
          ref={videoRef}
          className="absolute w-px h-px opacity-0"
          muted
          loop
          playsInline
          disablePictureInPicture
          preload="auto"
          aria-hidden
        >
          <source src="/mascot/fenki-idle-loop.webm" type="video/webm" />
          <source src="/mascot/fenki-idle-loop.mp4" type="video/mp4" />
        </video>
      )}

      <div className="absolute inset-0" style={EDGE_MASK}>
        {wantVideo && (
          <canvas
            ref={canvasRef}
            className={`w-full h-full object-cover ${MELT} ${playing ? "block" : "hidden"}`}
            aria-hidden
          />
        )}
        {/* still: shown until the canvas has frames, and for reduced-motion/fallback */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={still}
          alt="Fenki, the AdSpy fennec"
          className={`w-full h-full object-cover ${MELT} ${playing && wantVideo ? "hidden" : "block"}`}
          onError={(e) => {
            if (!e.currentTarget.src.endsWith("fenki-hero.webp")) {
              e.currentTarget.src = "/mascot/fenki-hero.webp";
            }
          }}
        />
      </div>
    </div>
  );
}
