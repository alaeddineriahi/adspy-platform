"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Fenki — the AdSpy mascot (white fennec, holo-gradient ears, red chachia).
 *
 * Assets sit on a uniform off-white (~242) background, no alpha. The page
 * behind him is NOT flat — decorative orbs tint it — so no uniform color
 * remap can ever match it; the only correct compositing is multiply
 * blending, which lets the real backdrop show through white pixels.
 *
 * Multiply silently fails in two ways, both handled here:
 *  1. A playing <video> gets promoted to a hardware overlay that ignores
 *     CSS → the video is a hidden decoder; a <canvas> mirrors its frames.
 *  2. ANY ancestor with a stacking context (CSS masks, fade-up animations,
 *     opacity, transforms) ISOLATES the blend — the canvas then blends
 *     against nothing and the box reappears. So: no mask (multiply makes
 *     white edges invisible on its own), no fade-up wrapper (the entrance
 *     fade is the canvas's own opacity transition, which does not isolate
 *     an element from its backdrop), and the in-canvas brightness remap
 *     pushes the 242 background to pure 255 so multiply erases it exactly.
 *
 * Stills (poses / reduced motion / video failure) run through the same
 * canvas + blend pipeline.
 */
export type MascotPose = "hero" | "hot" | "thinking" | "empty" | "celebrate";

const CROP_BOTTOM = 0.03;  // thin dark line at the video's very bottom edge

/**
 * Brightness factor that maps the background to pure white (255).
 * The video bg is ~242 but NOT perfectly uniform (compression noise dips it
 * a few levels), and multiply leaves a faint gray veil wherever a pixel
 * lands under the target — so calibrate against the DARKEST of several
 * background samples, minus a small safety margin, so every bg pixel clips
 * to 255 and vanishes completely.
 */
function bgScale(ctx: CanvasRenderingContext2D, w: number, h: number): number {
  try {
    const pts: [number, number][] = [
      [6, 6], [w - 7, 6], [6, Math.floor(h / 2)], [w - 7, Math.floor(h / 2)],
      [Math.floor(w / 2), 6], [6, h - 7],
    ];
    let darkest = 255;
    for (const [x, y] of pts) {
      const d = ctx.getImageData(x, y, 1, 1).data;
      darkest = Math.min(darkest, (d[0] + d[1] + d[2]) / 3);
    }
    return darkest > 170 && darkest < 254 ? 255 / (darkest - 3) : 1;
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
  const [ready, setReady] = useState(false);

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
        const scale = bgScale(ctx, canvas.width, canvas.height);
        if (scale !== 1 && "filter" in ctx) {
          ctx.filter = `brightness(${scale})`;
          ctx.drawImage(img, 0, 0);
          ctx.filter = "none";
        }
        setReady(true);
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
        // Render at display resolution, not the video's native size —
        // sharper enough, and ~10x less pixel work per frame.
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const dw = Math.min(sw, Math.round(size * 1.4 * dpr));
        const dh = Math.round(dw * (sh / sw));
        if (canvas.width !== dw || canvas.height !== dh) {
          canvas.width = dw;
          canvas.height = dh;
        }
        if (scale === null) {
          ctx.filter = "none";
          ctx.drawImage(video, 0, 0, sw, sh, 0, 0, dw, dh);
          scale = bgScale(ctx, dw, dh);
          setReady(true);
        }
        if (scale !== 1 && "filter" in ctx) ctx.filter = `brightness(${scale})`;
        ctx.drawImage(video, 0, 0, sw, sh, 0, 0, dw, dh);
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
  }, [wantVideo, size]);

  return (
    // NOTE: keep this wrapper free of stacking-context creators (no masks,
    // no animations, no opacity, no transforms, no z-index) or the canvas's
    // multiply blend gets isolated from the page and the white box returns.
    <div
      className={`relative mx-auto select-none pointer-events-none ${className}`}
      // min() caps the fixed size on small screens — a 560px box can't center
      // inside a 380px phone viewport, it just overflows to one side.
      style={{ width: `min(${size}px, 92vw)`, aspectRatio: "1 / 0.82" }}
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
        className="w-full h-full object-cover mix-blend-multiply transition-opacity duration-700"
        style={{ opacity: ready ? 1 : 0 }}
        role="img"
        aria-label="Fenki, the AdSpy fennec"
      />
    </div>
  );
}
