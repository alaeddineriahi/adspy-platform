"use client";

import { LucideIcon } from "lucide-react";

/**
 * The one page header — radar's design language everywhere:
 * gradient icon tile, black title (optional live pulse), gray subtitle,
 * staggered fade-up entrance.
 */
export function PageHeader({
  icon: Icon,
  gradient = "from-[#3e86c6] to-[#a666aa]",
  title,
  subtitle,
  live = false,
  children,
}: {
  icon: LucideIcon;
  gradient?: string;
  title: string;
  subtitle?: string;
  live?: boolean;
  children?: React.ReactNode; // right-side slot (actions, badges)
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-8">
      <div className="flex items-start gap-3.5 fade-up" style={{ ["--delay" as string]: "0ms" }}>
        <span
          className={`w-11 h-11 shrink-0 rounded-xl flex items-center justify-center text-white bg-gradient-to-br ${gradient} shadow-sm`}
        >
          <Icon className="w-5 h-5" />
        </span>
        <div>
          <h2 className="text-2xl font-black tracking-tight text-[#1d1d1f] flex items-center gap-2">
            {title}
            {live && <span className="radar-live-dot w-2 h-2 rounded-full bg-[#ec4492]" />}
          </h2>
          {subtitle && <p className="text-sm text-[#6e6e73] mt-0.5 max-w-xl">{subtitle}</p>}
        </div>
      </div>
      {children && (
        <div className="fade-up shrink-0" style={{ ["--delay" as string]: "120ms" }}>
          {children}
        </div>
      )}
    </div>
  );
}

/** Wrap grid items for the staggered entrance (delay capped so deep grids don't lag). */
export function Stagger({ index, children }: { index: number; children: React.ReactNode }) {
  return (
    <div className="fade-up" style={{ ["--delay" as string]: `${Math.min(index, 9) * 60}ms` }}>
      {children}
    </div>
  );
}
