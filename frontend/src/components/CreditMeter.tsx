"use client";

import Link from "next/link";
import { Sparkles } from "lucide-react";
import { useUsage } from "@/components/UsageProvider";

const PLAN_LABEL: Record<string, string> = { free: "Free", pro: "Pro", agency: "Agency" };

/** Sidebar widget: plan badge + AI-credit bar + upgrade nudge. */
export function CreditMeter() {
  const { usage } = useUsage();
  if (!usage) return null;

  const pct = usage.credits_limit
    ? Math.min(100, Math.round((usage.credits_used / usage.credits_limit) * 100))
    : 0;
  const low = usage.credits_remaining <= Math.max(2, usage.credits_limit * 0.1);
  const out = usage.credits_remaining <= 0;

  return (
    <div className="px-4 pb-3">
      <div className="bg-[#fbfbfb] border border-[#e6e6e7] rounded-2xl p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-[#1d1d1f] flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" /> AI credits
          </span>
          <span
            className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
              usage.plan === "free"
                ? "bg-gray-200 text-gray-600"
                : "holo-gradient text-white"
            }`}
          >
            {PLAN_LABEL[usage.plan] ?? usage.plan}
          </span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              out ? "bg-red-500" : low ? "bg-amber-500" : "holo-gradient"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className={`text-[11px] ${out ? "text-red-600 font-medium" : "text-[#6e6e73]"}`}>
            {usage.credits_used} / {usage.credits_limit} used
          </span>
          {(usage.plan === "free" || low) && (
            <Link
              href="/pricing"
              className="text-[11px] font-bold holo-text"
            >
              Upgrade →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
