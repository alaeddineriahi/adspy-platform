"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Fenki — the AdSpy mascot (white fennec, holo-gradient ears, red chachia).
 *
 * Assets sit on an OFF-white (~#f0f0f0) background with no alpha, and a
 * gradient bar is baked into the video's floor. Every CSS-level fix
 * (mix-blend-multiply + filter) failed in the wild for two reasons:
 *   1. playing <video> gets promoted to a hardware overlay that ignores CSS,
 *   2. the edge-fade mask creates an ISOLATED stacking context, inside which
 *      mix-blend-mode blends against nothing — so the box came back.
 *
 * So everything now happens in canvas pixels, immune to both:
 *   - a hidden <video> only decodes; the canvas mirrors its frames
 *   - the bottom 24% of each video frame (the gradient bar) is cropped
 *     at the SOURCE rect
 *   - the background is SAMPLED from a corner pixel and a brightness factor
 *     is computed so that bg becomes exactly the page color — the background
 *     isn't hidden, it's converted into the page
 *   - stills (poses, reduced-motion, fallback) run through the same canvas
 *     pipeline for a consistent look
 * The elliptical mask stays purely as a soft edge fade (no blending logic).
 */
export type MascotPose = "hero" | "hot" | "thinking" | "empty" | "celebrate";

const EDGE_MASK = {
  maskImage: "radial-gradient(ellipse 74% 70% at 50% 44%, black 60%, transparent 94%)",
  WebkitMaskImage: "radial-gradient(ellipse 74% 70% at 50% 44%, black 60%, transparent 94%)",
} as React.CSSProperties;

const PAGE_LUMA = 251;      // #fbfbfb — what the asset background must become
const CROP_BOTTOM = 0.24;   // video floor slice holding the baked-in gradient bar

/** brightness factor that maps the sampled background onto the page color */
function bgScale(ctx: CanvasRenderingContext2D): number {
  try {
    const d = ctx.getImageData(8, 8, 1, 1).data;
    const bg = (d[0] + d[1] + d[2]) / 3;
    return bg > 170 && bg < 254 ? PAGE_LUMA / bg : 1;
  } catch {
    return 1;
  }
}

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
  const [videoOk, setVideoOk] = useState(true);

  const still = pose === "hero" ? "/mascot/fenki-hero.webp" : `/mascot/fenki-${pose}.png`;
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wantVideo = animated && pose === "hero" && videoOk && !reducedMotion;

  // Still-image path (poses, reduced motion, video fallback) — same pipeline.
  useEffect(() => {
    if (wantVideo) return;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d", { willReadFrequently: true });
    if (!canvas || !ctx) return;
    let cancelled = false;

    const render = (src: string, isFallback = false) => {
      const img = new Image();
      img.onload = () => {
        if (cancelled) return;
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        ctx.filter = "none";
        ctx.drawImage(img, 0, 0);
        const scale = bgScale(ctx);
        if (scale !== 1 && "filter" in ctx) {
          ctx.filter = `brightness(${scale})`;
          ctx.drawImage(img, 0, 0);
          ctx.filter = "none";
        }
      };
      img.onerror = () => {
        if (!cancelled && !isFallback) render("/mascot/fenki-hero.webp", true);
      };
      img.src = src;
    };
    render(still);
    return () => { cancelled = true; };
  }, [wantVideo, still]);

  // Video path: hidden decoder → per-frame canvas mirror.
  useEffect(() => {
    if (!wantVideo) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d", { willReadFrequently: true });
    if (!video || !canvas || !ctx) return;

    let raf = 0;
    let scale: number | null = null;

    const draw = () => {
      if (video.readyState >= 2 && video.videoWidth) {
        const sw = video.videoWidth;
        const sh = Math.floor(video.videoHeight * (1 - CROP_BOTTOM));
        if (canvas.width !== sw || canvas.height !== sh) {
          canvas.width = sw;
          canvas.height = sh;
        }
        if (scale === null) {
          ctx.filter = "none";
          ctx.drawImage(video, 0, 0, sw, sh, 0, 0, sw, sh);
          scale = bgScale(ctx);
        }
        if (scale !== 1 && "filter" in ctx) ctx.filter = `brightness(${scale})`;
        ctx.drawImage(video, 0, 0, sw, sh, 0, 0, sw, sh);
        ctx.filter = "none";
      }
      raf = requestAnimationFrame(draw);
    };

    const onError = () => setVideoOk(false);
    video.addEventListener("error", onError);
    video.play().then(() => { raf = requestAnimationFrame(draw); }).catch(onError);

    return () => {
      cancelAnimationFrame(raf);
      video.removeEventListener("error", onError);
      video.pause();
    };
  }, [wantVideo]);

  return (
    <div
      className={`relative mx-auto select-none pointer-events-none ${className}`}
      style={{ width: size, height: size * 0.82 }}
    >
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
      <canvas
        ref={canvasRef}
        className="w-full h-full object-cover"
        style={EDGE_MASK}
        role="img"
        aria-label="Fenki, the AdSpy fennec"
      />
    </div>
  );
}
