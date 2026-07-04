"use client";

import Link from "next/link";
import { useUser, useClerk } from "@clerk/nextjs";
import { Settings, Sparkles, CreditCard, LogOut, UserCircle } from "lucide-react";
import { useUsage } from "@/components/UsageProvider";
import { PageHeader } from "@/components/PageHeader";

const PLAN_LABEL: Record<string, string> = { free: "Free", pro: "Pro", agency: "Agency" };

export default function SettingsPage() {
  const { user } = useUser();
  const { signOut, openUserProfile } = useClerk();
  const { usage } = useUsage();

  const pct = usage?.credits_limit
    ? Math.min(100, Math.round((usage.credits_used / usage.credits_limit) * 100))
    : 0;

  return (
    <div className="p-4 md:p-8 max-w-3xl mx-auto">
      <PageHeader
        icon={Settings}
        gradient="from-[#1d1d1f] to-[#6e6e73]"
        title="Settings"
        subtitle="Your account, plan, and AI credit usage."
      />

      {/* Account */}
      <div className="bg-white border border-[#e6e6e7] rounded-2xl p-6 mb-5 fade-up" style={{ ["--delay" as string]: "80ms" }}>
        <h3 className="text-sm font-bold text-[#1d1d1f] mb-4 flex items-center gap-1.5">
          <UserCircle className="w-4 h-4" /> Account
        </h3>
        <div className="flex items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {user?.imageUrl && (
            <img src={user.imageUrl} alt="" className="w-12 h-12 rounded-full border border-[#e6e6e7]" />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-[#1d1d1f] truncate">
              {user?.fullName || user?.primaryEmailAddress?.emailAddress}
            </p>
            <p className="text-xs text-[#6e6e73] truncate">{user?.primaryEmailAddress?.emailAddress}</p>
          </div>
          <button
            onClick={() => openUserProfile()}
            className="shrink-0 text-sm font-medium border border-[#e6e6e7] rounded-full px-4 py-2 hover:border-[#1d1d1f] transition"
          >
            Manage account
          </button>
        </div>
      </div>

      {/* Plan & credits */}
      <div className="bg-white border border-[#e6e6e7] rounded-2xl p-6 mb-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-[#1d1d1f] flex items-center gap-1.5">
            <Sparkles className="w-4 h-4" /> Plan & AI credits
          </h3>
          {usage && (
            <span
              className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                usage.plan === "free" ? "bg-gray-200 text-gray-600" : "holo-gradient text-white"
              }`}
            >
              {PLAN_LABEL[usage.plan] ?? usage.plan}
            </span>
          )}
        </div>

        {usage ? (
          <>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-2">
              <div className="h-full rounded-full holo-gradient transition-all" style={{ width: `${pct}%` }} />
            </div>
            <p className="text-sm text-[#6e6e73] mb-4">
              {usage.credits_used} of {usage.credits_limit} AI credits used this month —{" "}
              {usage.credits_remaining} left. Resets on the 1st.
            </p>
          </>
        ) : (
          <p className="text-sm text-[#6e6e73] mb-4">Loading your usage…</p>
        )}

        <Link href="/pricing" className="btn-holo inline-flex px-5 py-2 text-sm">
          <CreditCard className="w-4 h-4" />
          {usage?.plan === "free" ? "Upgrade plan" : "Manage plan"}
        </Link>
      </div>

      {/* Session */}
      <div className="bg-white border border-[#e6e6e7] rounded-2xl p-6">
        <h3 className="text-sm font-bold text-[#1d1d1f] mb-3">Session</h3>
        <button
          onClick={() => signOut({ redirectUrl: "/" })}
          className="inline-flex items-center gap-2 text-sm font-medium text-red-600 border border-red-200 rounded-full px-4 py-2 hover:bg-red-50 transition"
        >
          <LogOut className="w-4 h-4" /> Sign out
        </button>
      </div>
    </div>
  );
}
