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
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-3">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-700 flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" /> AI credits
          </span>
          <span
            className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
              usage.plan === "free"
                ? "bg-gray-200 text-gray-600"
                : "bg-blue-100 text-blue-700"
            }`}
          >
            {PLAN_LABEL[usage.plan] ?? usage.plan}
          </span>
        </div>
        <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              out ? "bg-red-500" : low ? "bg-amber-500" : "bg-blue-600"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className={`text-[11px] ${out ? "text-red-600 font-medium" : "text-gray-500"}`}>
            {usage.credits_used} / {usage.credits_limit} used
          </span>
          {(usage.plan === "free" || low) && (
            <Link
              href="/pricing"
              className="text-[11px] font-semibold text-blue-600 hover:text-blue-500"
            >
              Upgrade →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
